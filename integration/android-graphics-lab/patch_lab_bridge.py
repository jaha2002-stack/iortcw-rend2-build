#!/usr/bin/env python3
"""Graphics Lab native command bridge. Applied AFTER existing Android portability patch."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
path=root/"SP/code/client/cl_ui.c"
s=path.read_text()
needle="void CL_AndroidConsumeGameActions(void)"
assert needle in s, "Android portability patch not applied"
bridge=r'''
/* Graphics Lab: bounded, thread-safe SPSC command mailbox, executed on engine frame.
 * Never execute console commands from Android UI thread.
 */
static volatile int dwLabBusy;
static char dwLabCommand[512];
static volatile int dwLabReady;
JNIEXPORT void JNICALL
Java_org_darkwolf_rend2_DarkWolfActivity_nativeQueueLabCommand(
    JNIEnv *env, jclass clazz, jstring command)
{
    const char *text;
    size_t len;
    (void)clazz;
    if (!command) return;
    text=(*env)->GetStringUTFChars(env,command,NULL);
    if (!text) return;
    len=strlen(text);
    if (len && len<sizeof(dwLabCommand)-2 &&
        !strchr(text,';') && !strchr(text,'\\') && !strchr(text,'\n') &&
        !strchr(text,'\r') && !strchr(text,'"')) {
        if (__sync_lock_test_and_set(&dwLabBusy,1)==0) {
            if (!dwLabReady) {
                memcpy(dwLabCommand,text,len);
                dwLabCommand[len]='\n';
                dwLabCommand[len+1]='\0';
                __sync_synchronize();
                dwLabReady=1;
            }
            __sync_lock_release(&dwLabBusy);
        }
    }
    (*env)->ReleaseStringUTFChars(env,command,text);
}
static void CL_AndroidConsumeLabCommand(void)
{
    char local[sizeof(dwLabCommand)];
    if (!dwLabReady) return;
    if (__sync_lock_test_and_set(&dwLabBusy,1)!=0) return;
    if (!dwLabReady) {
        __sync_lock_release(&dwLabBusy);
        return;
    }
    memcpy(local,dwLabCommand,sizeof(local));
    dwLabReady=0;
    __sync_lock_release(&dwLabBusy);
    Cbuf_ExecuteText(EXEC_APPEND,local);
}
'''
s=s.replace(needle,bridge+"\n"+needle,1)
# Integrate at action consumption, exactly once per frame.
needle2="    androidGameAppliedMask = desired;"
assert needle2 in s
s=s.replace(needle2,needle2+"\n    CL_AndroidConsumeLabCommand();",1)
path.write_text(s)
print("GRAPHICS_LAB_JNI_BRIDGE=APPLIED")
