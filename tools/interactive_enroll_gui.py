#!/usr/bin/env python3
"""Experimental 5955 interactive enrolment GUI; never commits a template.

The Windows engine runs in a USB-free bubblewrap sandbox. A separate,
existing audited sudo helper reads fresh touches. Grayscale frames travel
through private anonymous pipes only; no image files are saved.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from live_contact_viewer import read_record
from raw_to_png import decode_samples, to_8bit

HERE=Path(__file__).resolve().parent
SCRIPT=HERE/"test_moh_isolated_interactive_enroll.sh"
HELPER=HERE/"auto_contact_capture.py"

class EnrolGUI:
    def __init__(self, root, archive):
        self.root=root
        self.archive=archive
        self.events=queue.Queue()
        self.stop_event=threading.Event()
        self.engine=None
        self.capture=None
        self.engine_ready=threading.Event()
        self.complete=False
        self.touches=0
        self.added=0
        self.last_feedback="none"
        root.title("FocalTech 5955 — Fingerprint enrolment")
        root.geometry("530x650")
        root.resizable(False,False)
        root.protocol("WM_DELETE_WINDOW",self.close)
        frame=ttk.Frame(root,padding=20)
        frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="Fingerprint enrolment",font=("Sans",17,"bold")).pack()
        ttk.Label(frame,text="Place your finger on the sensor. Lift fully between touches.",
                  wraplength=460,justify="center").pack(pady=(6,8))
        self.canvas=tk.Canvas(frame,width=260,height=330,highlightthickness=0)
        self.canvas.pack()
        self.draw_target("idle")
        self.status=tk.StringVar(value="Ready to start. No fingerprint template will be saved.")
        ttk.Label(frame,textvariable=self.status,wraplength=460,justify="center",
                  font=("Sans",11)).pack(pady=10)
        self.progress=tk.StringVar(value="Touches: 0   •   Accepted: 0   •   Status: NOT COMPLETE")
        ttk.Label(frame,textvariable=self.progress).pack(pady=3)
        buttons=ttk.Frame(frame)
        buttons.pack(pady=15)
        self.start_button=ttk.Button(buttons,text="Start enrolment",command=self.start)
        self.start_button.pack(side="left",padx=8)
        self.stop_button=ttk.Button(buttons,text="Stop",command=self.stop,state="disabled")
        self.stop_button.pack(side="left",padx=8)
        self.next_button=ttk.Button(frame,text="Continue: next eight touches",
                                    command=self.next_touches,state="disabled")
        self.next_button.pack()
        ttk.Label(frame,text="The target is illustrative, not an anatomical coverage map.\n"
                  "Guidance is based on returned enrolment status, not guessed edges.",
                  justify="center",wraplength=450).pack(pady=15)
        self.active=False
        root.after(100,self.drain)

    def draw_target(self,state):
        c=self.canvas
        c.delete("all")
        palette={"idle":"#7c8997","ready":"#277db5","added":"#169b64",
                 "reposition":"#d09027","complete":"#169b64","error":"#c0392b"}
        colour=palette.get(state,palette["idle"])
        c.create_oval(59,17,201,298,outline=colour,width=5)
        for i in range(11):
            inset=i*6
            c.create_arc(72+inset,32+inset,188-inset,278-inset,
                         start=20,extent=320,style="arc",outline=colour,width=2)
        c.create_oval(113,146,147,180,fill=colour,outline="")
        c.create_text(130,319,text="SENSOR TARGET",fill=colour,font=("Sans",10,"bold"))

    def update_progress(self):
        state="COMPLETE (in memory)" if self.complete else "NOT COMPLETE"
        self.progress.set(f"Touches: {self.touches}   •   Accepted: {self.added}   •   Status: {state}")

    def start(self):
        if self.active:return
        self.active=True
        self.complete=False
        self.touches=0
        self.added=0
        self.last_feedback="none"
        self.stop_event.clear()
        self.engine_ready.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.next_button.configure(state="disabled")
        self.draw_target("ready")
        self.update_progress()
        self.status.set("Initialising isolated FocalTech engine...")
        threading.Thread(target=self.start_engine,daemon=True).start()

    def start_engine(self):
        try:
            self.engine=subprocess.Popen(["bash",str(SCRIPT),str(self.archive)],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,bufsize=0,cwd=HERE.parent)
            threading.Thread(target=self.read_engine_diagnostics,daemon=True).start()
            for line in iter(self.engine.stdout.readline,b""):
                line=line.decode("utf-8","replace").strip()
                if line=="READY":
                    self.engine_ready.set()
                    self.events.put(("ready",))
                elif line.startswith("TOUCH ") or line.startswith("DONE ") or line.startswith("ERROR "):
                    self.events.put(("engine",line))
            if not self.stop_event.is_set() and not self.complete:
                self.events.put(("error","Engine process ended before enrolment completed. Check preflight and sandbox requirements."))
        except Exception as exc:
            self.events.put(("error",f"Engine start failed: {exc}"))

    def read_engine_diagnostics(self):
        """Consume verbose vendor logs, retaining only raw return codes."""
        try:
            for line in iter(self.engine.stderr.readline,b""):
                msg=line.decode("utf-8","replace")
                for part in msg.split("[5955] ENROLL_DIAG "):
                    if part.startswith(("update_hr=","status_hr=")):
                        self.events.put(("diagnostic",part.splitlines()[0].strip()))
        except (OSError,ValueError):
            pass

    def next_touches(self):
        if not self.engine_ready.is_set() or self.stop_event.is_set():return
        self.next_button.configure(state="disabled")
        threading.Thread(target=self.capture_session,daemon=True).start()

    def capture_session(self):
        try:
            proc=subprocess.Popen(["sudo","-n",sys.executable,str(HELPER)],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,cwd=HERE.parent,bufsize=0)
            self.capture=proc
            while not self.stop_event.is_set() and not self.complete:
                item=read_record(proc.stdout)
                if item is None: break
                kind,contents=item
                if kind==b"F":
                    frame=to_8bit(decode_samples(contents,"little"))
                    if len(frame)!=5120:raise ValueError("Invalid converted fingerprint dimensions")
                    if not self.engine or self.engine.poll() is not None:
                        raise RuntimeError("Engine no longer running")
                    self.engine.stdin.write(frame)
                    self.engine.stdin.flush()
                    self.events.put(("capture",))
                elif kind==b"S":
                    self.events.put(("sensor",contents.decode("utf-8","replace")))
                elif kind in (b"E",b"D"):
                    self.events.put(("sensor",contents.decode("utf-8","replace")))
                    break
            if proc.stdin and not proc.stdin.closed:proc.stdin.close()
            proc.wait(timeout=15)
            if not self.stop_event.is_set() and not self.complete:
                self.events.put(("session-end",))
        except Exception as exc:
            self.events.put(("error",f"Capture stopped: {exc}"))
        finally:
            self.capture=None

    def drain(self):
        while True:
            try: event=self.events.get_nowait()
            except queue.Empty:break
            kind=event[0]
            if kind=="ready":
                self.draw_target("ready")
                self.status.set("Engine ready. Lift finger, then touch sensor.")
                self.next_touches()
            elif kind=="capture":
                self.touches+=1
                self.update_progress()
            elif kind=="engine":
                parts=event[1].split()
                if parts[0]=="TOUCH" and len(parts)>=3:
                    code=parts[2]
                    if code=="added":
                        self.added+=1
                        self.draw_target("added")
                        self.status.set("Capture accepted. Lift and move finger slightly for new coverage.")
                    elif code=="reposition":
                        self.draw_target("reposition")
                        self.status.set("Too similar / reposition requested. Lift and move slightly.")
                    elif code=="bad-capture":
                        self.draw_target("error")
                        self.status.set("Capture rejected. Lift and try again.")
                    elif code=="complete":
                        self.complete=True
                        self.draw_target("complete")
                        self.status.set("Enrolment complete in engine memory. No template committed.")
                        self.stop()
                    self.progress.set(f"Touches: {self.touches}   •   Accepted: {self.added}")
                elif parts[0]=="DONE":
                    if parts[-1]=="complete":
                        self.complete=True
                        self.draw_target("complete")
                        self.status.set("Enrolment complete in memory. No template saved.")
                        self.stop()
                    elif not self.stop_event.is_set():
                        self.status.set("NOT ENROLLED — engine session ended: "+parts[-1])
                        self.stop()
                else:
                    self.events.put(("error",event[1]+"; last result: "+self.last_feedback))
            elif kind=="diagnostic":
                self.last_feedback=event[1]
                # Diagnostics are non-biometric: HRESULTs and rejection codes only.
                self.status.set("Engine diagnostic: "+event[1])
            elif kind=="sensor":
                if not self.complete:
                    self.status.set(event[1])
            elif kind=="session-end":
                if not self.complete and not self.stop_event.is_set():
                    self.next_button.configure(state="normal")
                    self.status.set("NOT ENROLLED YET — engine needs more useful captures. Use Continue for another eight touches, or Stop.")
            elif kind=="error":
                if not self.complete:
                    self.draw_target("error")
                    self.status.set("NOT ENROLLED — "+event[1])
                    self.stop()
        self.root.after(100,self.drain)

    def stop(self):
        self.stop_event.set()
        if self.capture and self.capture.stdin and not self.capture.stdin.closed:
            try:self.capture.stdin.write(b"q");self.capture.stdin.flush()
            except (OSError,ValueError):pass
        if self.engine and self.engine.stdin and not self.engine.stdin.closed:
            try:self.engine.stdin.close()
            except (OSError,ValueError):pass
        self.active=False
        self.update_progress()
        self.start_button.configure(state="normal")
        self.next_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")

    def close(self):
        self.stop()
        self.root.destroy()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--send",action="store_true")
    args=p.parse_args()
    if not args.send:p.error("Use --send to authorise bounded sensor interaction")
    if os.geteuid()==0:p.error("Run GUI as regular user; use sudo -v separately")
    if not args.archive.is_file():p.error("Windows driver archive not found")
    root=tk.Tk()
    EnrolGUI(root,args.archive.resolve())
    root.mainloop()
if __name__=="__main__":
    main()
