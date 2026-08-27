from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config_store import load_existing_config, write_json_config
from sftp_host_keys import save_server_host_key, select_known_hosts


VERSION = "1.8.0"


def _int(value, default: int, minimum: int = 0, maximum: int = 65535) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def find_sqlite_candidates() -> list[Path]:
    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        return []
    root = Path(appdata) / "djsoft.net"
    candidates: list[Path] = []
    shared = root / "tracks.db"
    if shared.is_file():
        candidates.append(shared)
    candidates.extend(sorted(p for p in root.glob("RadioBOSS_*/tracks.db") if p.is_file()))
    return candidates


def test_sqlite(path: Path) -> tuple[bool, str]:
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name IN ('tracks2','taginfo')")
        found = {row[0] for row in cursor.fetchall()}
        cursor.close(); connection.close()
        missing = {"tracks2", "taginfo"} - found
        if missing:
            return False, "Missing table(s): " + ", ".join(sorted(missing))
        return True, f"RadioBOSS database OK: {path}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def test_mysql(values: dict) -> tuple[bool, str]:
    try:
        import mysql.connector
    except ImportError:
        return False, "mysql-connector-python is not available."
    try:
        connection = mysql.connector.connect(
            host=values["db_host"].strip(),
            port=_int(values["db_port"], 3306, 1, 65535),
            database=values["db_name"].strip(),
            user=values["db_user"].strip(),
            password=values["db_password"],
            charset=values["db_charset"].strip() or "utf8mb4",
            connection_timeout=7,
            use_pure=True,
        )
        cursor = connection.cursor()
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_name IN ('tracks2','taginfo')",
            (values["db_name"].strip(),),
        )
        found = {row[0] for row in cursor.fetchall()}
        cursor.close(); connection.close()
        missing = {"tracks2", "taginfo"} - found
        if missing:
            return False, "Missing table(s): " + ", ".join(sorted(missing))
        return True, "MySQL/MariaDB connection successful."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


async def _test_sftp_async(values: dict, app_dir: Path) -> tuple[bool, str]:
    try:
        import asyncssh
    except ImportError:
        return False, "asyncssh is not available."
    host = values["sftp_host"].strip(); port = _int(values["sftp_port"], 22, 1, 65535)
    username = values["sftp_username"].strip(); password = values["sftp_password"]
    key_file = values["sftp_private_key_file"].strip(); passphrase = values["sftp_private_key_passphrase"]
    timeout = _int(values["sftp_timeout"], 20, 1, 120)
    configured_known_hosts = str(
        values.get("sftp_known_hosts_file", "sftp_known_hosts")
    )
    client_keys = []; preferred_auth = "password,keyboard-interactive"
    if key_file:
        key_path = Path(key_file).expanduser()
        if not key_path.is_absolute(): key_path = app_dir / key_path
        if not key_path.is_file(): return False, f"Private key not found: {key_path}"
        client_keys = [asyncssh.read_private_key(str(key_path), passphrase=passphrase or None)]
        password = None; preferred_auth = "publickey"
    try:
        known_hosts_file, known_hosts, trust_first_connection = select_known_hosts(
            app_dir,
            configured_known_hosts,
            bool(values["sftp_trust_on_first_use"]),
        )
        async with asyncssh.connect(
            host, port=port, username=username, password=password or None,
            known_hosts=known_hosts, client_keys=client_keys, preferred_auth=preferred_auth,
            agent_path=None, login_timeout=timeout,
        ) as connection:
            if trust_first_connection:
                save_server_host_key(
                    connection,
                    host,
                    port,
                    known_hosts_file,
                )
            async with connection.start_sftp_client() as sftp:
                public_dir = values["sftp_remote_public_dir"].strip(); private_dir = values["sftp_remote_private_dir"].strip()
                if not await sftp.isdir(public_dir): return False, f"Remote public directory not found: {public_dir}"
                if not await sftp.isdir(private_dir): return False, f"Remote private directory not found: {private_dir}"
        message = "SFTP connection and remote directories are OK."
        if trust_first_connection:
            message += " The server key was saved automatically."
        return True, message
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def test_sftp(values: dict, app_dir: Path) -> tuple[bool, str]:
    if not values["sftp_enabled"]:
        return True, "SFTP is disabled."
    return asyncio.run(_test_sftp_async(values, app_dir))


def build_config(v: dict) -> dict:
    return {
        "CONFIG_VERSION": 1,
        "DB_TYPE": str(v["db_type"]),
        "SQLITE_MODE": str(v["sqlite_mode"]),
        "SQLITE_DATABASE": str(v["sqlite_database"]),
        "DB_HOST": str(v["db_host"]),
        "DB_PORT": _int(v["db_port"], 3306, 1, 65535),
        "DB_NAME": str(v["db_name"]),
        "DB_USER": str(v["db_user"]),
        "DB_PASSWORD": str(v["db_password"]),
        "DB_CHARSET": str(v["db_charset"] or "utf8mb4"),
        "PUBLIC_EXPORT_DIR": str(v["public_export_dir"]),
        "PRIVATE_EXPORT_DIR": str(v["private_export_dir"]),
        "SCHEDULER_EXPORT_ENABLED": bool(v["scheduler_export_enabled"]),
        "SCHEDULER_SDL_FILE": str(v["scheduler_sdl_file"]),
        "SHOW_EXAMPLES": bool(v["show_examples"]),
        "EXAMPLE_LIMIT": _int(v["example_limit"], 10, 0, 1000),
        "SFTP_ENABLED": bool(v["sftp_enabled"]),
        "SFTP_HOST": str(v["sftp_host"]),
        "SFTP_PORT": _int(v["sftp_port"], 22, 1, 65535),
        "SFTP_USERNAME": str(v["sftp_username"]),
        "SFTP_PASSWORD": str(v["sftp_password"]),
        "SFTP_PRIVATE_KEY_FILE": str(v["sftp_private_key_file"]),
        "SFTP_PRIVATE_KEY_PASSPHRASE": str(
            v["sftp_private_key_passphrase"]
        ),
        "SFTP_REMOTE_PUBLIC_DIR": str(v["sftp_remote_public_dir"]),
        "SFTP_REMOTE_PRIVATE_DIR": str(v["sftp_remote_private_dir"]),
        "SFTP_TIMEOUT": _int(v["sftp_timeout"], 20, 1, 120),
        "SFTP_TRUST_ON_FIRST_USE": bool(v["sftp_trust_on_first_use"]),
        "SFTP_KNOWN_HOSTS_FILE": "sftp_known_hosts",
    }


class SetupWizard(tk.Tk):
    def __init__(self, app_dir: Path):
        super().__init__()
        self.app_dir = app_dir
        self.config_path = app_dir / "config.json"
        self.legacy_config_path = app_dir / "config.py"
        self.existing = load_existing_config(
            self.config_path,
            self.legacy_config_path,
        )
        self.title(f"RadioBOSS SongSync Setup v{VERSION}"); self.geometry("820x720"); self.minsize(740,640); self.result=False
        self._make_variables(); self.db_test_status=tk.StringVar(value="Not tested yet."); self.sftp_test_status=tk.StringVar(value="Not tested yet."); self.notebook=ttk.Notebook(self); self.notebook.pack(fill="both",expand=True,padx=12,pady=(12,4))
        self._database_tab(); self._export_tab(); self._sftp_tab(); self._review_tab()
        bottom=ttk.Frame(self); bottom.pack(fill="x",padx=12,pady=10)
        ttk.Button(bottom,text="Cancel",command=self._cancel).pack(side="left")
        ttk.Button(bottom,text="Back",command=self._back).pack(side="right",padx=(6,0))
        ttk.Button(bottom,text="Next",command=self._next).pack(side="right",padx=(6,0))
        ttk.Button(bottom,text="Save configuration",command=self._save).pack(side="right")
        self.protocol("WM_DELETE_WINDOW",self._cancel)

    def _v(self,name,default=""): return self.existing.get(name,default)
    def _make_variables(self):
        self.vars={
            "db_type":tk.StringVar(value=str(self._v("DB_TYPE","sqlite"))), "sqlite_mode":tk.StringVar(value=str(self._v("SQLITE_MODE","dedicated"))),
            "sqlite_database":tk.StringVar(value=str(self._v("SQLITE_DATABASE","auto"))), "db_host":tk.StringVar(value=str(self._v("DB_HOST","127.0.0.1"))),
            "db_port":tk.StringVar(value=str(self._v("DB_PORT",3306))), "db_name":tk.StringVar(value=str(self._v("DB_NAME","radioboss"))),
            "db_user":tk.StringVar(value=str(self._v("DB_USER","radioboss_readonly"))), "db_password":tk.StringVar(value=str(self._v("DB_PASSWORD",""))),
            "db_charset":tk.StringVar(value=str(self._v("DB_CHARSET","utf8mb4"))), "public_export_dir":tk.StringVar(value=str(self._v("PUBLIC_EXPORT_DIR","exports/public"))),
            "private_export_dir":tk.StringVar(value=str(self._v("PRIVATE_EXPORT_DIR","exports/private"))), "show_examples":tk.BooleanVar(value=bool(self._v("SHOW_EXAMPLES",True))),
            "scheduler_export_enabled":tk.BooleanVar(value=bool(self._v("SCHEDULER_EXPORT_ENABLED",False))), "scheduler_sdl_file":tk.StringVar(value=str(self._v("SCHEDULER_SDL_FILE",""))),
            "example_limit":tk.StringVar(value=str(self._v("EXAMPLE_LIMIT",10))), "sftp_enabled":tk.BooleanVar(value=bool(self._v("SFTP_ENABLED",False))),
            "sftp_host":tk.StringVar(value=str(self._v("SFTP_HOST","your-sftp-server.example"))), "sftp_port":tk.StringVar(value=str(self._v("SFTP_PORT",22))),
            "sftp_username":tk.StringVar(value=str(self._v("SFTP_USERNAME",""))), "sftp_password":tk.StringVar(value=str(self._v("SFTP_PASSWORD",""))),
            "sftp_private_key_file":tk.StringVar(value=str(self._v("SFTP_PRIVATE_KEY_FILE","sftp_key" if (self.app_dir / "sftp_key").is_file() else ""))), "sftp_private_key_passphrase":tk.StringVar(value=str(self._v("SFTP_PRIVATE_KEY_PASSPHRASE",""))),
            "sftp_remote_public_dir":tk.StringVar(value=str(self._v("SFTP_REMOTE_PUBLIC_DIR","/path/to/songrequest/data/public"))),
            "sftp_remote_private_dir":tk.StringVar(value=str(self._v("SFTP_REMOTE_PRIVATE_DIR","/path/to/songrequest/data/private"))),
            "sftp_timeout":tk.StringVar(value=str(self._v("SFTP_TIMEOUT",20))), "sftp_trust_on_first_use":tk.BooleanVar(value=bool(self._v("SFTP_TRUST_ON_FIRST_USE",True))),
            "sftp_known_hosts_file":tk.StringVar(value=str(self._v("SFTP_KNOWN_HOSTS_FILE","sftp_known_hosts"))),
        }

    def _row(self,parent,row,label,variable,password=False,browse=None):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",padx=8,pady=6)
        ttk.Entry(parent,textvariable=variable,show="*" if password else "").grid(row=row,column=1,sticky="ew",padx=8,pady=6)
        if browse: ttk.Button(parent,text="Browse...",command=browse).grid(row=row,column=2,padx=8,pady=6)
        parent.columnconfigure(1,weight=1)

    def _database_tab(self):
        tab=ttk.Frame(self.notebook); self.notebook.add(tab,text="1. Database")
        choice=ttk.LabelFrame(tab,text="Database type"); choice.pack(fill="x",padx=12,pady=12)
        ttk.Radiobutton(choice,text="SQLite (standard RadioBOSS)",variable=self.vars["db_type"],value="sqlite").pack(anchor="w",padx=10,pady=5)
        ttk.Radiobutton(choice,text="MySQL / MariaDB",variable=self.vars["db_type"],value="mysql").pack(anchor="w",padx=10,pady=5)
        sb=ttk.LabelFrame(tab,text="SQLite"); sb.pack(fill="x",padx=12,pady=8)
        ttk.Label(sb,text="Mode").grid(row=0,column=0,sticky="w",padx=8,pady=6)
        ttk.Combobox(sb,textvariable=self.vars["sqlite_mode"],values=("dedicated","shared"),state="readonly").grid(row=0,column=1,sticky="ew",padx=8,pady=6)
        self._row(sb,1,"Database",self.vars["sqlite_database"],browse=self._browse_sqlite)
        ttk.Button(sb,text="Detect RadioBOSS databases",command=self._detect_sqlite).grid(row=2,column=1,sticky="w",padx=8,pady=6); sb.columnconfigure(1,weight=1)
        mb=ttk.LabelFrame(tab,text="MySQL / MariaDB"); mb.pack(fill="x",padx=12,pady=8)
        for r,(lab,key,pw) in enumerate([("Host","db_host",False),("Port","db_port",False),("Database","db_name",False),("User","db_user",False),("Password","db_password",True),("Charset","db_charset",False)]):
            self._row(mb,r,lab,self.vars[key],password=pw)
        ttk.Button(tab,text="Test database connection",command=self._test_database).pack(anchor="w",padx=20,pady=(10,4))
        ttk.Label(tab,textvariable=self.db_test_status,wraplength=720).pack(anchor="w",padx=20,pady=(0,10))

    def _export_tab(self):
        tab=ttk.Frame(self.notebook); self.notebook.add(tab,text="2. Exports")
        box=ttk.LabelFrame(tab,text="Local JSON export"); box.pack(fill="x",padx=12,pady=12)
        self._row(box,0,"Public export directory",self.vars["public_export_dir"]); self._row(box,1,"Private export directory",self.vars["private_export_dir"])
        scheduler=ttk.LabelFrame(tab,text="Private scheduler-event export"); scheduler.pack(fill="x",padx=12,pady=8)
        ttk.Checkbutton(scheduler,text="Export playlist events for Radio Music Analytics",variable=self.vars["scheduler_export_enabled"]).grid(row=0,column=0,columnspan=3,sticky="w",padx=8,pady=6)
        self._row(scheduler,1,"RadioBOSS Admin.sdl",self.vars["scheduler_sdl_file"],browse=self._browse_sdl)
        ttk.Label(scheduler,text="Only path-safe event metadata is exported; local Windows paths remain private.",wraplength=700).grid(row=2,column=0,columnspan=3,sticky="w",padx=8,pady=(2,8))
        ttk.Checkbutton(tab,text="Show example catalog entries after export",variable=self.vars["show_examples"]).pack(anchor="w",padx=20,pady=10)
        line=ttk.Frame(tab); line.pack(fill="x",padx=20); ttk.Label(line,text="Number of examples").pack(side="left"); ttk.Entry(line,textvariable=self.vars["example_limit"],width=10).pack(side="left",padx=10)
        ttk.Label(tab,text="Public files contain the searchable catalog. Private files contain the filename lookup and must not be publicly downloadable.",wraplength=700).pack(anchor="w",padx=20,pady=18)

    def _sftp_tab(self):
        tab=ttk.Frame(self.notebook); self.notebook.add(tab,text="3. SFTP")
        ttk.Checkbutton(tab,text="Upload generated files automatically with SFTP",variable=self.vars["sftp_enabled"]).pack(anchor="w",padx=20,pady=12)
        box=ttk.LabelFrame(tab,text="SFTP connection"); box.pack(fill="x",padx=12,pady=8)
        fields=[("Host","sftp_host",False,None),("Port","sftp_port",False,None),("Username","sftp_username",False,None),("Password","sftp_password",True,None),
                ("Private key file","sftp_private_key_file",False,self._browse_key),("Key passphrase","sftp_private_key_passphrase",True,None),
                ("Remote public directory","sftp_remote_public_dir",False,None),("Remote private directory","sftp_remote_private_dir",False,None),
                ("Timeout (seconds)","sftp_timeout",False,None)]
        for r,(lab,key,pw,browse) in enumerate(fields): self._row(box,r,lab,self.vars[key],password=pw,browse=browse)
        ttk.Checkbutton(box,text="Trust server key on first successful connection",variable=self.vars["sftp_trust_on_first_use"]).grid(row=9,column=1,sticky="w",padx=8,pady=6)
        ttk.Button(tab,text="Test SFTP connection",command=self._test_sftp).pack(anchor="w",padx=20,pady=(10,4))
        ttk.Label(tab,textvariable=self.sftp_test_status,wraplength=720).pack(anchor="w",padx=20,pady=(0,10))

    def _review_tab(self):
        tab=ttk.Frame(self.notebook); self.notebook.add(tab,text="4. Review")
        ttk.Label(tab,text="Review the settings, then click Save configuration. Passwords remain only in the local config.json file.",wraplength=700).pack(anchor="w",padx=20,pady=14)
        self.review=tk.Text(tab,height=24,wrap="word",state="disabled"); self.review.pack(fill="both",expand=True,padx=20,pady=10)
        self.notebook.bind("<<NotebookTabChanged>>",lambda _e:self._refresh_review())

    def values(self): return {k:v.get() for k,v in self.vars.items()}
    def _browse_sqlite(self):
        p=filedialog.askopenfilename(title="Select RadioBOSS tracks.db",filetypes=[("RadioBOSS database","tracks.db"),("Database files","*.db"),("All files","*.*")])
        if p:self.vars["sqlite_database"].set(p)
    def _browse_key(self):
        p=filedialog.askopenfilename(title="Select SSH private key",filetypes=[("All files","*.*")])
        if p:
            try:self.vars["sftp_private_key_file"].set(str(Path(p).resolve().relative_to(self.app_dir.resolve())))
            except ValueError:self.vars["sftp_private_key_file"].set(p)
    def _browse_sdl(self):
        p=filedialog.askopenfilename(title="Select RadioBOSS Admin.sdl",filetypes=[("RadioBOSS scheduler","*.sdl"),("All files","*.*")])
        if p:self.vars["scheduler_sdl_file"].set(p)
    def _detect_sqlite(self):
        c=find_sqlite_candidates()
        if not c: messagebox.showwarning("SQLite detection","No RadioBOSS tracks.db database was found."); return
        chosen=c[0]
        if len(c)>1: messagebox.showinfo("SQLite databases found","Multiple databases were found. The first was selected; use Browse to choose another.\n\n"+"\n".join(str(x) for x in c))
        self.vars["sqlite_database"].set(str(chosen)); self.vars["sqlite_mode"].set("shared" if chosen.parent.name=="djsoft.net" else "dedicated")
    def _test_database(self):
        self.db_test_status.set("Testing...")
        self.update_idletasks()

        try:
            v = self.values()

            if v["db_type"] == "sqlite":
                configured = v["sqlite_database"].strip()

                if configured.lower() == "auto":
                    candidates = find_sqlite_candidates()
                    candidates = [
                        path for path in candidates
                        if (path.parent.name == "djsoft.net")
                        == (v["sqlite_mode"] == "shared")
                    ]

                    if len(candidates) != 1:
                        self.db_test_status.set(
                            "Not tested: use Detect or Browse to select tracks.db."
                        )
                        return

                    database_path = candidates[0]
                else:
                    database_path = Path(configured).expanduser()
                    if not database_path.is_absolute():
                        database_path = self.app_dir / database_path

                ok, message = test_sqlite(database_path)
            else:
                ok, message = test_mysql(v)

            prefix = "OK: " if ok else "ERROR: "
            self.db_test_status.set(prefix + message)

        except Exception as exc:
            self.db_test_status.set(
                f"ERROR: {type(exc).__name__}: {exc}"
            )
        finally:
            # Keep the main wizard visible and focused after testing.
            try:
                self.deiconify()
                self.lift()
                self.focus_force()
            except tk.TclError:
                pass
    def _test_sftp(self):
        self.sftp_test_status.set("Testing...")
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            v=self.values()
            ok,msg=test_sftp(v,self.app_dir)
            self.sftp_test_status.set(("OK: " if ok else "ERROR: ") + msg)
        except Exception as exc:
            self.sftp_test_status.set(f"ERROR: {type(exc).__name__}: {exc}")
        finally:
            self.config(cursor="")
            try:
                self.deiconify(); self.lift(); self.focus_force()
            except tk.TclError:
                pass
    def _refresh_review(self):
        if self.notebook.index(self.notebook.select())!=3:return
        v=self.values(); lines=[f"Database type: {v['db_type']}",f"SQLite mode: {v['sqlite_mode']}",f"SQLite database: {v['sqlite_database']}","",f"Public export: {v['public_export_dir']}",f"Private export: {v['private_export_dir']}",f"Scheduler export: {'Yes' if v['scheduler_export_enabled'] else 'No'}",f"Scheduler SDL: {v['scheduler_sdl_file'] if v['scheduler_export_enabled'] else '-'}","",f"SFTP enabled: {'Yes' if v['sftp_enabled'] else 'No'}",f"SFTP host: {v['sftp_host'] if v['sftp_enabled'] else '-'}",f"SFTP user: {v['sftp_username'] if v['sftp_enabled'] else '-'}",f"Remote public: {v['sftp_remote_public_dir'] if v['sftp_enabled'] else '-'}",f"Remote private: {v['sftp_remote_private_dir'] if v['sftp_enabled'] else '-'}","","Passwords are hidden from this review."]
        self.review.config(state="normal"); self.review.delete("1.0","end"); self.review.insert("1.0","\n".join(lines)); self.review.config(state="disabled")
    def _back(self):
        i=self.notebook.index(self.notebook.select()); self.notebook.select(max(0,i-1))
    def _next(self):
        i=self.notebook.index(self.notebook.select()); self.notebook.select(min(self.notebook.index("end")-1,i+1))
    def _save(self):
        v=self.values()
        if v["db_type"] not in {"sqlite","mysql"}: messagebox.showerror("Configuration","Choose SQLite or MySQL/MariaDB."); return
        if v["db_type"]=="sqlite" and v["sqlite_mode"] not in {"shared","dedicated"}: messagebox.showerror("Configuration","SQLite mode must be shared or dedicated."); return
        if v["scheduler_export_enabled"]:
            configured=Path(v["scheduler_sdl_file"].strip()).expanduser()
            if not configured.is_absolute(): configured=self.app_dir/configured
            if not configured.is_file() or configured.suffix.lower()!=".sdl": messagebox.showerror("Configuration","Select an existing RadioBOSS .sdl file for scheduler export."); return
        if v["sftp_enabled"]:
            missing=[n for n,val in [("SFTP host",v["sftp_host"]),("SFTP username",v["sftp_username"]),("Remote public directory",v["sftp_remote_public_dir"]),("Remote private directory",v["sftp_remote_private_dir"])] if not str(val).strip()]
            if missing: messagebox.showerror("Configuration","Missing: "+", ".join(missing)); return
            if not v["sftp_password"] and not v["sftp_private_key_file"]: messagebox.showerror("Configuration","Enter an SFTP password or private key."); return
        try:
            backup_path = write_json_config(self.config_path, build_config(v))
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror(
                "Configuration",
                f"Could not replace config.json:\n{exc}",
            )
            return
        message = "Configuration saved successfully."
        if backup_path is not None:
            message += "\n\nThe previous file was saved as config.json.bak."
        message += "\n\nSongSync will now continue with this configuration."
        self.result = True
        messagebox.showinfo("SongSync setup", message)
        self.destroy()
    def _cancel(self): self.result=False; self.destroy()


def run_setup(app_dir: Path) -> bool:
    app=SetupWizard(app_dir); app.mainloop(); return bool(app.result)


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def write_startup_error(exc: BaseException) -> None:
    try:
        log_path = application_dir() / "setup-error.log"
        log_path.write_text(
            "RadioBOSS SongSync Setup startup error\n"
            "======================================\n\n"
            + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
            newline="\n",
        )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        base = application_dir()
        success = run_setup(base)
        raise SystemExit(0 if success else 1)
    except SystemExit:
        raise
    except BaseException as exc:
        write_startup_error(exc)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "RadioBOSS SongSync Setup",
                "The Setup Wizard could not start.\n\n"
                "Details were written to setup-error.log next to the EXE.",
            )
            root.destroy()
        except Exception:
            pass
        raise SystemExit(1)
