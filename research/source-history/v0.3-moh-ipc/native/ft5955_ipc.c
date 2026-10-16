#define _POSIX_C_SOURCE 200809L
/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_ipc.h"
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static int64_t now_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) return -1;
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec/1000000;
}
static int wait_fd(int fd, short ev, int64_t deadline) {
    for (;;) {
        int64_t remaining = deadline - now_ms();
        if (remaining <= 0) return -1;
        struct pollfd p = { .fd=fd, .events=ev };
        int ret = poll(&p,1,(int)(remaining>2147483647?2147483647:remaining));
        if (ret < 0 && errno == EINTR) continue;
        if (ret <= 0 || (p.revents & (POLLERR|POLLNVAL))) return -1;
        if (p.revents & ev) return 0;
        return -1;
    }
}
static int write_all(int fd, const void *bytes, size_t size, int64_t deadline) {
    const uint8_t *data=bytes;
    while (size) {
        if (wait_fd(fd,POLLOUT,deadline)) return -1;
        ssize_t n=send(fd,data,size,MSG_NOSIGNAL);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) return -1;
        data+=n;size-=(size_t)n;
    }
    return 0;
}
static int readline_bounded(int fd, char out[FT5955_REPLY_BYTES], int64_t deadline) {
    size_t n=0;
    out[0]='\0';
    for (;;) {
        if (wait_fd(fd,POLLIN,deadline)) return -1;
        char c;
        ssize_t k=recv(fd,&c,1,0);
        if (k<0 && errno==EINTR) continue;
        if (k!=1 || n>=FT5955_REPLY_BYTES-1) return -1;
        if (c=='\n') {out[n]='\0';return 0;}
        if ((unsigned char)c<0x20 || (unsigned char)c>0x7e) return -1;
        out[n++]=c;
    }
}
static int exchange(Ft5955Ipc *ipc, const char *command,
                    const uint8_t *frame, char reply[FT5955_REPLY_BYTES]) {
    if (!ipc || !ipc->running || !reply) return -1;
    int64_t deadline=now_ms()+ipc->timeout_ms;
    if (write_all(ipc->to_child,command,strlen(command),deadline)) return -1;
    if (frame && write_all(ipc->to_child,frame,FT5955_FRAME_BYTES,deadline)) return -1;
    if (readline_bounded(ipc->from_child,reply,deadline)) return -1;
    if (!reply[0]) return -1;
    return 0;
}
static void close_fd(int *p) { if (*p>=0) {close(*p);*p=-1;} }
static void reap_bounded(pid_t pid) {
    if (pid<=0) return;
    int st;
    int64_t until=now_ms()+1200;
    while (now_ms()<until) {
        pid_t got=waitpid(pid,&st,WNOHANG);
        if (got==pid || (got<0 && errno==ECHILD)) return;
        if (got<0 && errno!=EINTR) return;
        struct timespec pause={.tv_sec=0,.tv_nsec=20000000};
        nanosleep(&pause,NULL);
    }
    kill(pid,SIGTERM);
    until=now_ms()+1200;
    while (now_ms()<until) {
        pid_t got=waitpid(pid,&st,WNOHANG);
        if (got==pid || (got<0 && errno==ECHILD)) return;
        if (got<0 && errno!=EINTR) return;
        struct timespec pause={.tv_sec=0,.tv_nsec=20000000};
        nanosleep(&pause,NULL);
    }
    kill(pid,SIGKILL);
    while (waitpid(pid,&st,0)<0 && errno==EINTR) {}
}
void ft5955_ipc_close(Ft5955Ipc *ipc) {
    if (!ipc) return;
    if (ipc->running && ipc->to_child>=0) {
        char response[FT5955_REPLY_BYTES];
        /* Ask for graceful shutdown and consume BYE before closing stdout.
         * Timeout/failure falls back to bounded termination below. */
        (void)exchange(ipc,"QUIT\n",NULL,response);
    }
    close_fd(&ipc->to_child);
    close_fd(&ipc->from_child);
    if (ipc->pid>0) reap_bounded(ipc->pid);
    ipc->pid=-1;
    ipc->running=0;
}
int ft5955_ipc_start(Ft5955Ipc *ipc, const char *python,
                     const char *adapter, const char *runner, int timeout_ms) {
    if (!ipc || !python || !adapter || !runner || timeout_ms<100 || timeout_ms>180000)
        return -1;
    /* Caller supplies a fresh/closed Ft5955Ipc, never an active instance. */
    if (ipc->running) return -1;
    ipc->pid=-1;ipc->to_child=-1;ipc->from_child=-1;
    ipc->timeout_ms=timeout_ms;
    int to[2]={-1,-1},from[2]={-1,-1};
    if (socketpair(AF_UNIX,SOCK_STREAM,0,to) ||
        socketpair(AF_UNIX,SOCK_STREAM,0,from)) goto fail;
    pid_t pid=fork();
    if (pid<0) goto fail;
    if (pid==0) {
        if (dup2(to[0],STDIN_FILENO)<0 || dup2(from[1],STDOUT_FILENO)<0) _exit(127);
        close(to[0]);close(to[1]);close(from[0]);close(from[1]);
        execlp(python,python,adapter,"--runner",runner,"--timeout","90",(char*)NULL);
        _exit(127);
    }
    ipc->pid=pid;
    close(to[0]);to[0]=-1;
    close(from[1]);from[1]=-1;
    ipc->to_child=to[1];to[1]=-1;
    ipc->from_child=from[0];from[0]=-1;
    if (fcntl(ipc->to_child,F_SETFL,fcntl(ipc->to_child,F_GETFL)|O_NONBLOCK)<0) goto fail;
    if (fcntl(ipc->from_child,F_SETFL,fcntl(ipc->from_child,F_GETFL)|O_NONBLOCK)<0) goto fail;
    ipc->running=1;
    char reply[FT5955_REPLY_BYTES];
    if (exchange(ipc,"HELLO\n",NULL,reply) || strcmp(reply,"READY 2")) goto fail;
    return 0;
fail:
    if (to[0]>=0) close(to[0]);
    if (to[1]>=0) close(to[1]);
    if (from[0]>=0) close(from[0]);
    if (from[1]>=0) close(from[1]);
    ft5955_ipc_close(ipc);
    return -1;
}
int ft5955_ipc_begin(Ft5955Ipc *ipc,int slot,char reply[FT5955_REPLY_BYTES]) {
    if (slot!=1 && slot!=2) return -1;
    return exchange(ipc,slot==1?"BEGIN 1\n":"BEGIN 2\n",NULL,reply);
}
int ft5955_ipc_sample(Ft5955Ipc *ipc,const uint8_t frame[FT5955_FRAME_BYTES],
                      char reply[FT5955_REPLY_BYTES]) {
    if (!frame) return -1;
    return exchange(ipc,"SAMPLE\n",frame,reply);
}
int ft5955_ipc_verify(Ft5955Ipc *ipc,const uint8_t frame[FT5955_FRAME_BYTES],
                      char reply[FT5955_REPLY_BYTES]) {
    if (!frame) return -1;
    return exchange(ipc,"VERIFY\n",frame,reply);
}
int ft5955_ipc_cancel(Ft5955Ipc *ipc,char reply[FT5955_REPLY_BYTES]) {
    return exchange(ipc,"CANCEL\n",NULL,reply);
}

Ft5955Result ft5955_ipc_decode(const char *reply, int *stage) {
    if (stage) *stage=0;
    if (!reply) return FT5955_R_INVALID;
    if (!strcmp(reply,"BEGIN OK")) return FT5955_R_BEGIN;
    if (!strcmp(reply,"RETRY QUALITY")) return FT5955_R_RETRY;
    if (!strcmp(reply,"COMPLETE")) return FT5955_R_COMPLETE;
    if (!strcmp(reply,"MATCH 1")) return FT5955_R_MATCH_1;
    if (!strcmp(reply,"MATCH 2")) return FT5955_R_MATCH_2;
    if (!strcmp(reply,"NO_MATCH")) return FT5955_R_NO_MATCH;
    if (!strcmp(reply,"AMBIGUOUS")) return FT5955_R_AMBIGUOUS;
    if (!strcmp(reply,"CANCELLED")) return FT5955_R_CANCELLED;
    if (!strncmp(reply,"ERROR ",6)) return FT5955_R_ERROR;
    int n=-1; char tail='\0';
    if (sscanf(reply,"PROGRESS %d 12%c",&n,&tail)==1 && n>=1 && n<=11) {
        if (stage) *stage=n;
        return FT5955_R_PROGRESS;
    }
    return FT5955_R_INVALID;
}
