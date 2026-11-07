/* Protocol 1, single-client loopback helper. No Wine/native focus assumptions
 * beyond verified Win32 foreground. All input is scan-code based; Alt forbidden. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0600
#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#define LINE_MAX_BYTES 4096
#define FIELD_MAX 8
#define TEXT_MAX 512
#define FOCUS_ATTEMPTS 3
#define FOCUS_RETRY_MS 30
static CRITICAL_SECTION input_lock;
static ULONGLONG held[2][128];
static volatile LONG stopping;
static ULONGLONG max_hold_ms = 10000;
static HWND target;
static DWORD target_pid;
static char process_name[TEXT_MAX];
static const char *token;
static FILE *log_file;

typedef struct { char name[32], text[TEXT_MAX]; char type; long number; } Field;
typedef struct { Field fields[FIELD_MAX]; int count; } Request;
static void log_event(const char *event) {
    if (log_file) { fprintf(log_file, "%llu %s\n", GetTickCount64(), event); fflush(log_file); }
}
static int inject(int scan, int ext, int down) {
    INPUT in = {0};
    in.type = INPUT_KEYBOARD;
    in.ki.wScan = (WORD)scan;
    in.ki.dwFlags = KEYEVENTF_SCANCODE | (ext ? KEYEVENTF_EXTENDEDKEY : 0) |
                      (down ? 0 : KEYEVENTF_KEYUP);
    return SendInput(1, &in, sizeof(in)) == 1;
}
/* Failed releases remain tracked so subsequent ticks retry them. */
static int release_keys(char *list, size_t cap, int expired_only) {
    size_t n = 0;
    int ok = 1;
    ULONGLONG now = GetTickCount64();
    if (list) list[0] = '\0';
    EnterCriticalSection(&input_lock);
    for (int e = 0; e < 2; e++) for (int s = 1; s < 128; s++) {
        if (!held[e][s] || (expired_only && now - held[e][s] < max_hold_ms)) continue;
        if (!inject(s, e, 0)) { ok = 0; continue; }
        held[e][s] = 0;
        if (list && n < cap) n += (size_t)snprintf(list+n, cap-n, "%s%d", n ? "," : "", s);
    }
    LeaveCriticalSection(&input_lock);
    return ok;
}
static void cleanup_input(void) { release_keys(NULL, 0, 0); }
static BOOL WINAPI console_stop(DWORD event) {
    (void)event;
    InterlockedExchange(&stopping, 1);
    cleanup_input();
    return TRUE;
}
static LRESULT CALLBACK window_proc(HWND hwnd, UINT msg, WPARAM w, LPARAM l) {
    if (msg == WM_QUERYENDSESSION) return TRUE;
    if ((msg == WM_ENDSESSION && w) || msg == WM_CLOSE) {
        InterlockedExchange(&stopping, 1); cleanup_input(); return 0;
    }
    return DefWindowProcA(hwnd, msg, w, l);
}
static void whitespace(const char **p) { while (**p && strchr(" \t\r\n", **p)) ++*p; }
/* Bounded JSON subset: flat protocol objects, ASCII strings and JSON scalars.
 * Unknown fields, duplicate fields, arrays, nested objects and NUL are rejected. */
static int string_value(const char **p, char *out, size_t cap) {
    size_t n = 0;
    if (*(*p)++ != '"') return 0;
    while (**p && **p != '"') {
        unsigned char ch = (unsigned char)*(*p)++;
        if (ch < 32 || ch > 126) return 0;
        if (ch == '\\') {
            ch = (unsigned char)*(*p)++;
            if (ch == 'u') {
                unsigned value = 0;
                for (int i = 0; i < 4; i++) {
                    unsigned char h = (unsigned char)**p;
                    if (!h || !isxdigit(h)) return 0;
                    ++*p; value = value * 16 + (isdigit(h) ? h-'0' : tolower(h)-'a'+10);
                }
                if (value < 32 || value > 126) return 0;
                ch = (unsigned char)value;
            } else if (ch != '"' && ch != '\\' && ch != '/') return 0;
        }
        if (n+1 >= cap) return 0;
        out[n++] = (char)ch;
    }
    if (**p != '"') return 0;
    ++*p; out[n] = 0; return 1;
}
static int parse(const char *p, Request *r) {
    r->count = 0; whitespace(&p);
    if (*p++ != '{') return 0;
    whitespace(&p);
    if (*p == '}') return 0;
    for (;;) {
        if (r->count == FIELD_MAX) return 0;
        Field *f = &r->fields[r->count];
        memset(f, 0, sizeof(*f));
        if (!string_value(&p, f->name, sizeof(f->name))) return 0;
        for (int i=0; i<r->count; i++) if (!strcmp(f->name, r->fields[i].name)) return 0;
        whitespace(&p); if (*p++ != ':') return 0; whitespace(&p);
        if (*p == '"') { f->type='s'; if (!string_value(&p,f->text,sizeof(f->text))) return 0; }
        else if (!strncmp(p,"true",4)) { f->type='b'; f->number=1; p+=4; }
        else if (!strncmp(p,"false",5)) { f->type='b'; p+=5; }
        else if (isdigit((unsigned char)*p)) {
            f->type='n';
            if (*p == '0' && isdigit((unsigned char)p[1])) return 0;
            do { f->number=f->number*10+(*p++-'0'); if (f->number>65535) return 0; }
            while (isdigit((unsigned char)*p));
        } else return 0;
        r->count++; whitespace(&p);
        if (*p == '}') { p++; whitespace(&p); return !*p; }
        if (*p++ != ',') return 0;
        whitespace(&p);
    }
}
static Field *field(Request *r, const char *name, char type) {
    for (int i=0; i<r->count; i++) if (!strcmp(r->fields[i].name,name) && r->fields[i].type==type) return &r->fields[i];
    return NULL;
}
static int process_for(HWND hwnd, char *out, size_t cap, DWORD *pid) {
    char path[2048]; DWORD length=sizeof(path);
    *pid=0; out[0]=0;
    if (!hwnd || !GetWindowThreadProcessId(hwnd,pid)) return 0;
    HANDLE h=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,*pid);
    if (!h) return 0;
    int ok=QueryFullProcessImageNameA(h,0,path,&length);
    CloseHandle(h);
    if (!ok) return 0;
    const char *base=strrchr(path,'\\'); base=base ? base+1 : path;
    if (strlen(base)>=cap) return 0;
    strcpy(out,base); return 1;
}
static int target_alive(void) {
    char name[TEXT_MAX]; DWORD pid;
    return IsWindow(target) && process_for(target,name,sizeof(name),&pid) &&
           pid==target_pid && !_stricmp(name,process_name);
}
static BOOL CALLBACK find_window(HWND hwnd, LPARAM unused) {
    char name[TEXT_MAX]; DWORD pid; (void)unused;
    if (IsWindowVisible(hwnd) && !GetWindow(hwnd,GW_OWNER) &&
        process_for(hwnd,name,sizeof(name),&pid) && !_stricmp(name,process_name)) {
        target=hwnd; target_pid=pid; return FALSE;
    }
    return TRUE;
}
static int resolve_target(void) {
    target=NULL; target_pid=0;
    if (*process_name) EnumWindows(find_window,0);
    return target != NULL;
}
static void attach_input(DWORD cur, DWORD other, BOOL on) {
    if (other && other!=cur) AttachThreadInput(cur,other,on);
}
/* A long-lived process loses the foreground right a fresh one has, and winemac
 * moves the Win32 foreground to the desktop when the Mac app is deactivated.
 * Escalate within a bounded retry: plain SetForegroundWindow, then share input
 * state with both the current foreground thread and the target's thread. */
static int focus_target(const char **step) {
    *step="already";
    if (GetForegroundWindow()==target) return 1;
    LockSetForegroundWindow(LSFW_UNLOCK);
    AllowSetForegroundWindow(ASFW_ANY);
    for (int attempt=0; attempt<FOCUS_ATTEMPTS; attempt++) {
        if (attempt) Sleep(FOCUS_RETRY_MS);
        *step="set_foreground"; SetForegroundWindow(target);
        if (GetForegroundWindow()==target) return 1;
        HWND fg=GetForegroundWindow();
        DWORD cur=GetCurrentThreadId(), other=GetWindowThreadProcessId(target,NULL);
        DWORD owner=fg ? GetWindowThreadProcessId(fg,NULL) : 0;
        *step="attach_thread_input";
        attach_input(cur,owner,TRUE);
        if (owner!=other) attach_input(cur,other,TRUE);
        BringWindowToTop(target); SetForegroundWindow(target); SetActiveWindow(target); SetFocus(target);
        if (owner!=other) attach_input(cur,other,FALSE);
        attach_input(cur,owner,FALSE);
        if (GetForegroundWindow()==target) return 1;
    }
    char name[TEXT_MAX], line[TEXT_MAX+64]; DWORD pid;
    if (!process_for(GetForegroundWindow(),name,sizeof(name),&pid)) strcpy(name,"?");
    snprintf(line,sizeof(line),"focus_failed fg=%s err=%lu",name,(unsigned long)GetLastError());
    log_event(line); return 0;
}
static void quote(const char *src, char *out) {
    *out++='"';
    for (; *src; src++) {
        unsigned char c=(unsigned char)*src;
        if (c=='"' || c=='\\') *out++='\\';
        *out++=(c>=32 && c<127) ? (char)c : '?';
    }
    *out++='"'; *out=0;
}
static void error_reply(char *out, const char *error) {
    snprintf(out,LINE_MAX_BYTES,"{\"ok\":false,\"error\":\"%s\",\"detail\":\"%s\"}\n",error,error);
}
static int dispatch(const char *line, int *authenticated, char *out) {
    Request r; Field *op;
    strcpy(out,"{\"ok\":true}\n");
    if (!parse(line,&r) || !(op=field(&r,"op",'s'))) goto bad;
    if (!strcmp(op->text,"hello")) {
        Field *t=field(&r,"token",'s'), *v=field(&r,"protocol",'n');
        *authenticated=0;
        if (r.count!=3 || !t || !v || v->number!=1) goto bad;
        if (strcmp(t->text,token)) { error_reply(out,"bad_token"); return 0; }
        *authenticated=1;
        strcpy(out,"{\"ok\":true,\"helper_version\":\"0.1.0\",\"protocol\":1}\n"); return 0;
    }
    if (!*authenticated) { error_reply(out,"bad_token"); return 0; }
    if (!strcmp(op->text,"target")) {
        Field *p=field(&r,"process",'s');
        if (r.count!=2 || !p || !*p->text || strpbrk(p->text,"/\\")) goto bad;
        cleanup_input(); strcpy(process_name,p->text);
        if (!resolve_target()) { error_reply(out,"no_target"); return 0; }
        snprintf(out,LINE_MAX_BYTES,"{\"ok\":true,\"hwnd\":\"0x%llx\",\"pid\":%lu}\n",(unsigned long long)(UINT_PTR)target,(unsigned long)target_pid);
    } else if (!strcmp(op->text,"key")) {
        Field *s=field(&r,"scan",'n'), *e=field(&r,"ext",'b'), *d=field(&r,"down",'b');
        if (r.count!=4 || !s || !e || !d || s->number<1 || s->number>127 || s->number==0x38) goto bad;
        if (d->number && !target_alive()) { error_reply(out,"no_target"); return 0; }
        /* Foreground can move between focus and a later down press; re-focus once. */
        if (d->number && GetForegroundWindow()!=target) {
            const char *step;
            if (!focus_target(&step)) { error_reply(out,"focus_failed"); return 0; }
            log_event(step);
        }
        EnterCriticalSection(&input_lock);
        if (d->number && InterlockedCompareExchange(&stopping,0,0)) {
            error_reply(out,"input_failed");
        } else if (inject((int)s->number,(int)e->number,(int)d->number)) {
            ULONGLONG *h=&held[e->number][s->number];
            if (!d->number) *h=0;
            else if (!*h) { *h=GetTickCount64(); if (!*h) *h=1; }
        } else error_reply(out,"input_failed");
        LeaveCriticalSection(&input_lock);
    } else {
        if (r.count!=1) goto bad;
        if (!strcmp(op->text,"focus")) {
            char before[TEXT_MAX], encoded[TEXT_MAX*2+3]; DWORD pid;
            process_for(GetForegroundWindow(),before,sizeof(before),&pid); quote(before,encoded);
            if (!target_alive() && !resolve_target()) { error_reply(out,"no_target"); return 0; }
            const char *step;
            if (!focus_target(&step)) { error_reply(out,"focus_failed"); return 0; }
            log_event(step);
            snprintf(out,LINE_MAX_BYTES,"{\"ok\":true,\"step\":\"%s\",\"fg_before\":%s}\n",step,encoded);
        } else if (!strcmp(op->text,"release_all")) {
            char list[2048];
            if (!release_keys(list,sizeof(list),0)) error_reply(out,"input_failed");
            else snprintf(out,LINE_MAX_BYTES,"{\"ok\":true,\"released\":[%s]}\n",list);
        } else if (!strcmp(op->text,"status")) {
            char name[TEXT_MAX], encoded[TEXT_MAX*2+3], list[2048]={0}; DWORD pid; size_t n=0;
            process_for(GetForegroundWindow(),name,sizeof(name),&pid); quote(name,encoded);
            EnterCriticalSection(&input_lock);
            for (int e=0;e<2;e++) for (int s=1;s<128;s++) if (held[e][s]) n+=(size_t)snprintf(list+n,sizeof(list)-n,"%s%d",n ? "," : "",s);
            LeaveCriticalSection(&input_lock);
            snprintf(out,LINE_MAX_BYTES,"{\"ok\":true,\"fg\":%s,\"target_alive\":%s,\"held\":[%s]}\n",encoded,target_alive() ? "true" : "false",list);
        } else if (!strcmp(op->text,"bye")) { cleanup_input(); return 1; }
        else goto bad;
    }
    return 0;
bad: error_reply(out,"bad_request"); return 0;
}
static int send_reply(SOCKET client, const char *out) {
    int left=(int)strlen(out);
    while (left) {
        int n=send(client,out,left,0);
        if (n<=0) return 0; /* Never block the watchdog for a stalled reader. */
        out+=n; left-=n;
    }
    return 1;
}
int main(int argc, char **argv) {
    int port=47811, result=1; const char *log_path=NULL;
    for (int i=1;i<argc;i+=2) {
        if (i+1>=argc) goto usage;
        char *end; const char *v=argv[i+1];
        if (!strcmp(argv[i],"--port")) { long p=strtol(v,&end,10); if (!*v || *end || p<1 || p>65535) goto usage; port=(int)p; }
        else if (!strcmp(argv[i],"--token")) token=v;
        else if (!strcmp(argv[i],"--log")) log_path=v;
        else if (!strcmp(argv[i],"--max-hold-s")) { double s=strtod(v,&end); if (!*v || *end || !isfinite(s) || s<0.001 || s>86400) goto usage; max_hold_ms=(ULONGLONG)(s*1000); }
        else goto usage;
    }
    if (!token || !*token || strlen(token)>=TEXT_MAX) goto usage;
    if (log_path && !(log_file=fopen(log_path,"a"))) { perror("log"); return 1; }
    InitializeCriticalSection(&input_lock); atexit(cleanup_input);
    SystemParametersInfoA(SPI_SETFOREGROUNDLOCKTIMEOUT,0,(PVOID)0,0); /* Session only, never persisted. */
    SetConsoleCtrlHandler(console_stop,TRUE);
    WNDCLASSA wc={0}; wc.lpfnWndProc=window_proc; wc.hInstance=GetModuleHandle(NULL); wc.lpszClassName="EdapInputHelper";
    if (!RegisterClassA(&wc)) return 1;
    HWND window=CreateWindowA(wc.lpszClassName,"",0,0,0,0,0,NULL,NULL,wc.hInstance,NULL);
    if (!window) return 1;
    WSADATA ws; if (WSAStartup(MAKEWORD(2,2),&ws)) return 1;
    SOCKET server=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP), client=INVALID_SOCKET;
    if (server==INVALID_SOCKET) goto done;
    BOOL exclusive=TRUE;
    if (setsockopt(server,SOL_SOCKET,SO_EXCLUSIVEADDRUSE,(const char *)&exclusive,sizeof(exclusive))) goto done;
    struct sockaddr_in addr={0}; addr.sin_family=AF_INET; addr.sin_port=htons((u_short)port); addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if (bind(server,(struct sockaddr *)&addr,sizeof(addr)) || listen(server,1)) goto done;
    u_long nonblock=1; if (ioctlsocket(server,FIONBIO,&nonblock)) goto done;
    char line[LINE_MAX_BYTES], out[LINE_MAX_BYTES]; size_t used=0; int authenticated=0, discard=0;
    log_event("listening"); result=0;
    while (!InterlockedCompareExchange(&stopping,0,0)) {
        MSG msg; while (PeekMessage(&msg,NULL,0,0,PM_REMOVE)) { TranslateMessage(&msg); DispatchMessage(&msg); }
        if (InterlockedCompareExchange(&stopping,0,0)) break;
        release_keys(NULL,0,1);
        if (target && !target_alive()) cleanup_input();
        fd_set reads; FD_ZERO(&reads); FD_SET(server,&reads); if (client!=INVALID_SOCKET) FD_SET(client,&reads);
        struct timeval wait={0,20000};
        if (select(0,&reads,NULL,NULL,&wait)==SOCKET_ERROR) { result=1; break; }
        if (FD_ISSET(server,&reads)) {
            SOCKET next=accept(server,NULL,NULL);
            if (next!=INVALID_SOCKET) {
                if (client!=INVALID_SOCKET || ioctlsocket(next,FIONBIO,&nonblock)) closesocket(next);
                else { client=next; authenticated=0; used=0; discard=0; }
            }
        }
        if (client==INVALID_SOCKET || !FD_ISSET(client,&reads)) continue;
        char chunk[1024]; int n=recv(client,chunk,sizeof(chunk),0), close_client=0;
        if (n<=0) close_client=1;
        for (int i=0;i<n && !close_client;i++) {
            if (chunk[i]=='\n') {
                int quit=0;
                if (discard) error_reply(out,"bad_request");
                else { line[used]=0; quit=dispatch(line,&authenticated,out); }
                used=0; discard=0;
                if (!send_reply(client,out)) close_client=1;
                if (quit) { InterlockedExchange(&stopping,1); close_client=1; }
            } else if (!discard) {
                if (!chunk[i] || used>=sizeof(line)-1) { discard=1; used=0; }
                else line[used++]=chunk[i];
            }
        }
        if (close_client) { cleanup_input(); closesocket(client); client=INVALID_SOCKET; log_event("disconnected"); }
    }
done:
    cleanup_input();
    if (client!=INVALID_SOCKET) closesocket(client);
    if (server!=INVALID_SOCKET) closesocket(server);
    WSACleanup(); DestroyWindow(window);
    if (log_file) fclose(log_file);
    return result;
usage:
    fprintf(stderr,"usage: edap_input_helper --port 47811 --token TOKEN --log PATH --max-hold-s 10.0\n"); return 2;
}
