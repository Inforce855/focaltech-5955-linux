#!/usr/bin/env python3
"""Experimental 5955 interactive enrolment GUI.

The vendor engine runs in a USB-free bubblewrap sandbox and uses the
offline-validated enrollment, duplicate-check and mock-storage commit
sequence. A bounded sudo helper reads fresh touches. Grayscale frames travel
through private anonymous pipes only and are inverted in memory to match
the higher-quality Windows-like polarity. The temporary biometric template
is committed ONLY to mock sandbox storage, then wiped; no image files,
persistent templates, PAM or operating-system biometric database changes.
"""
from __future__ import annotations
import argparse
import math
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
        self.rejected=0
        self.capture_running=False
        self.last_feedback="none"
        root.title("FocalTech 5955 — live experimental enrolment")
        root.geometry("530x650")
        root.resizable(False,False)
        root.protocol("WM_DELETE_WINDOW",self.close)
        frame=ttk.Frame(root,padding=20)
        frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="Fingerprint enrolment",font=("Sans",17,"bold")).pack()
        ttk.Label(frame,text="Place your finger on the sensor. Lift fully between touches.",
                  wraplength=460,justify="center").pack(pady=(6,4))
        ttk.Label(frame,text="12 usable touches required • Windows-like inverted polarity • no fingerprint saved",
                  wraplength=460,justify="center").pack(pady=(0,8))
        self.canvas=tk.Canvas(frame,width=260,height=330,highlightthickness=0)
        self.canvas.pack()
        self.draw_target("idle")
        self.status=tk.StringVar(value="Ready to start. Live enrolment is experimental; no fingerprint will be saved.")
        ttk.Label(frame,textvariable=self.status,wraplength=460,justify="center",
                  font=("Sans",11)).pack(pady=10)
        self.diagnostic=tk.StringVar(value="Last engine result: awaiting first capture")
        ttk.Label(frame,textvariable=self.diagnostic,wraplength=480,justify="center",
                  font=("Sans",9)).pack(pady=(0,6))
        self.progress=tk.StringVar(value="Touches: 0   •   Usable: 0   •   Rejected: 0   •   NOT COMPLETE")
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
                  "A completed session does not enrol Linux login or create a persistent template.",
                  justify="center",wraplength=450).pack(pady=15)
        self.active=False
        root.after(100,self.drain)

    def draw_target(self,state):
        """Draw an illustrative fingerprint ridge pattern, never biometric data."""
        c=self.canvas
        c.delete("all")
        palette={"idle":"#7c8997","ready":"#277db5","added":"#169b64",
                 "reposition":"#d09027","rejected":"#d09027",
                 "complete":"#169b64","error":"#c0392b"}
        colour=palette.get(state,palette["idle"])
        # Open-ended, asymmetrical fingerprint ridges. These are not
        # concentric ovals, nor a map of the user's actual fingerprint.
        for ring in range(11):
            radius=73-ring*4.5
            crest=26+ring*7.3
            arch_height=76-ring*2.6
            left_bottom=252-ring*3.1
            right_bottom=238-ring*2.7
            points=[130-radius,left_bottom,130-radius,crest+arch_height]
            for j in range(101):
                theta=math.pi*(1-j/100)
                x=130+radius*math.cos(theta)+2.8*math.sin(2*theta+ring*.17)
                y=crest+arch_height*(1-math.sin(theta))
                points.extend((x,y))
            points.extend((130+radius,crest+arch_height,130+radius,right_bottom))
            c.create_line(*points,fill=colour,width=2,smooth=True,
                          splinesteps=5,capstyle=tk.ROUND)
        # Core ridge flow: curved, separate tracks; no artificial centre dot.
        for ring in range(5):
            points=[]
            for j in range(90):
                t=j/89
                x=116+7*ring+9*math.sin(1.5*math.pi*t+ring*.20)
                y=152+90*t-4*ring
                points.extend((x,y))
            c.create_line(*points,fill=colour,width=2,smooth=True,
                          capstyle=tk.ROUND)
        c.create_text(130,307,text="FINGERPRINT TARGET",fill=colour,
                      font=("Sans",10,"bold"))

    def update_progress(self):
        state="COMPLETE (temporary; not saved)" if self.complete else "NOT COMPLETE"
        self.progress.set(f"Touches: {self.touches}   •   Usable: {self.added}   •   Rejected: {self.rejected}   •   {state}")

    def start(self):
        if self.active:return
        self.active=True
        self.complete=False
        self.touches=0
        self.added=0
        self.rejected=0
        self.last_feedback="none"
        self.diagnostic.set("Last engine result: awaiting first capture")
        self.capture_running=False
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
                    if part.startswith(("create_hr=","update_hr=","status_hr=")):
                        self.events.put(("diagnostic",part.splitlines()[0].strip()))
        except (OSError,ValueError):
            pass

    def next_touches(self):
        if not self.active or self.stop_event.is_set() or self.capture_running:
            return
        if not self.engine_ready.is_set() or not self.engine or self.engine.poll() is not None:
            self.status.set("Engine is not running. Select Start enrolment to begin a new session.")
            self.stop()
            return
        self.capture_running=True
        self.next_button.configure(state="disabled")
        self.status.set("Waiting for finger release and a fresh touch...")
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
                    # Match offline-proven high-quality polarity; never save
                    # or alter the physical capture. This is the same 255-p
                    # in-memory operation used by replay_moh_enrollment.py.
                    frame=bytes(255-value for value in frame)
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
            self.events.put(("capture-finished",))

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
                        self.status.set("Frame processed; engine still needs more data. Lift finger between touches.")
                    elif code in ("reposition","rejected"):
                        self.rejected+=1
                        self.draw_target("reposition")
                        self.status.set("Capture rejected (poor image quality / insufficient usable coverage). Stop and investigate if repeated.")
                    elif code=="bad-capture":
                        self.rejected+=1
                        self.draw_target("error")
                        self.status.set("Capture rejected by engine. Check reason in diagnostic line.")
                    elif code=="complete":
                        self.added+=1
                        self.complete=True
                        self.draw_target("complete")
                        self.status.set("12-touch enrolment completed and template created in sandbox memory, then wiped. Nothing saved.")
                        self.stop()
                    self.update_progress()
                elif parts[0]=="DONE":
                    if parts[-1]=="complete":
                        self.complete=True
                        self.draw_target("complete")
                        self.status.set("Enrolment and temporary in-memory commit complete. Template wiped; nothing saved.")
                        self.stop()
                    elif not self.stop_event.is_set():
                        self.status.set("NOT ENROLLED — engine session ended: "+parts[-1])
                        self.stop()
                else:
                    self.events.put(("error",event[1]+"; last result: "+self.last_feedback))
            elif kind=="diagnostic":
                self.last_feedback=event[1]
                # Diagnostics are non-biometric: HRESULTs and rejection codes only.
                detail=event[1]
                if "update_reject=7" in detail or "status_reject=7" in detail:
                    detail+=" (WINBIO_FP_POOR_QUALITY)"
                self.diagnostic.set("Last engine result: "+detail)
            elif kind=="sensor":
                if not self.complete:
                    self.status.set(event[1])
            elif kind=="session-end":
                if not self.complete and not self.stop_event.is_set():
                    self.status.set("NOT ENROLLED YET — capture batch ended. Repeating captures may not help; stop if progress stalls.")
            elif kind=="capture-finished":
                self.capture_running=False
                if self.active and not self.complete and not self.stop_event.is_set():
                    if self.engine and self.engine.poll() is None:
                        self.next_button.configure(state="normal")
                        self.status.set("NOT ENROLLED YET — you may Continue, but investigate repeated quality rejections first.")
                    else:
                        self.status.set("Engine stopped. Click Start enrolment for a new session.")
                        self.stop()
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
        self.capture_running=False
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
