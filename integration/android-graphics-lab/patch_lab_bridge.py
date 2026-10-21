#!/usr/bin/env python3
"""Graphics Lab native command bridge. Applied AFTER existing Android portability patch."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
path=root/"SP/code/client/cl_ui.c"
s=path.read_text()
assert "#include <jni.h>" in s
s=s.replace("#include <jni.h>", "#include <jni.h>\n#include <pthread.h>", 1)
ci_scene=r'''
/* CI-only: force the RTCW briefing closed, then prove the engine is actively
 * rendering with no menu catcher. Never enabled on ARM64 phone by default. */
static int dwLabCiFrames;
static int dwLabCiAnnounced;
static void CL_AndroidCIGameViewGate(void)
{
    if (!Cvar_VariableIntegerValue("dw_android_ci_playerstart"))
        return;
    if (cls.state != CA_ACTIVE)
        return;
    if (Key_GetCatcher() & KEYCATCH_UI) {
        if (uivm)
            VM_Call(uivm, UI_SET_ACTIVE_MENU, UIMENU_NONE);
        Key_SetCatcher(Key_GetCatcher() & ~KEYCATCH_UI);
        Cvar_Set("cl_paused", "0");
        dwLabCiFrames = 0;
    } else if (!dwLabCiAnnounced && ++dwLabCiFrames >= 90) {
        dwLabCiAnnounced = 1;
        Com_Printf("GRAPHICS_LAB_CI_GAMEVIEW=PASS\n");
    }
}
'''
needle="void CL_AndroidConsumeGameActions(void)"
assert needle in s, "Android portability patch not applied"
bridge=r'''
/* GRAPHICS_LAB_V02: serialized UI commands, drained on the engine thread. */
#define DW_LAB_QUEUE_CAP 64
#define DW_LAB_CMD_CAP 256
static pthread_mutex_t dwLabQueueLock = PTHREAD_MUTEX_INITIALIZER;
static char dwLabCommands[DW_LAB_QUEUE_CAP][DW_LAB_CMD_CAP];
static unsigned dwLabCmdRead, dwLabCmdWrite;
JNIEXPORT void JNICALL
Java_org_darkwolf_rend2_DarkWolfActivity_nativeQueueLabCommand(
    JNIEnv *env, jclass clazz, jstring command)
{
    const char *text;
    char key[80], value[80];
    size_t len;
    (void)clazz;
    if (!command) return;
    text = (*env)->GetStringUTFChars(env,command,NULL);
    if (!text) return;
    len = strlen(text);
    if (!len || len >= DW_LAB_CMD_CAP-2 || strchr(text,';') ||
        strchr(text,'\\') || strchr(text,'\n') ||
        strchr(text,'\r') || strchr(text,'"'))
        goto out;
    /* Canonical production guards must not be overridden by the lab UI. */
    key[0] = value[0] = 0;
    if (sscanf(text,"%79s %79s",key,value)==2) {
        if ((!Q_stricmp(key,"r_dlightmode") && strcmp(value,"2")) ||
            (!Q_stricmp(key,"r_forcesun") && strcmp(value,"1")))
            goto out;
    }
    pthread_mutex_lock(&dwLabQueueLock);
    if (dwLabCmdWrite-dwLabCmdRead < DW_LAB_QUEUE_CAP) {
        char *dst = dwLabCommands[dwLabCmdWrite % DW_LAB_QUEUE_CAP];
        memcpy(dst,text,len);
        dst[len]='\n';
        dst[len+1]='\0';
        ++dwLabCmdWrite;
    }
    pthread_mutex_unlock(&dwLabQueueLock);
out:
    (*env)->ReleaseStringUTFChars(env,command,text);
}
static void CL_AndroidConsumeLabCommand(void)
{
    int i;
    for (i=0; i<8; ++i) {
        char local[DW_LAB_CMD_CAP];
        pthread_mutex_lock(&dwLabQueueLock);
        if (dwLabCmdRead==dwLabCmdWrite) {
            pthread_mutex_unlock(&dwLabQueueLock);
            return;
        }
        memcpy(local,dwLabCommands[dwLabCmdRead % DW_LAB_QUEUE_CAP],
               sizeof(local));
        ++dwLabCmdRead;
        pthread_mutex_unlock(&dwLabQueueLock);
        Cbuf_ExecuteText(EXEC_APPEND,local);
    }
}
'''
catalog=r'''
/* Engine-thread catalog. The UI thread only reads a mutex-protected snapshot.
 * Includes all registered CVars, their reset values, latches and flags.
 * No direct UI-thread walk of cvar_vars; no CVar mutation here.
 */
#define DW_LAB_CATALOG_CAP (256*1024)
extern cvar_t *cvar_vars;
static pthread_mutex_t dwLabCatalogLock = PTHREAD_MUTEX_INITIALIZER;
static char dwLabCatalogPending[DW_LAB_CATALOG_CAP];
static char dwLabCatalogPublished[DW_LAB_CATALOG_CAP];
static unsigned dwLabCatalogTick;
static void DWLabCleanField(char *dst, size_t cap, const char *src)
{
    size_t i=0;
    if (!src) src="";
    while (i+1<cap && src[i]) {
        unsigned char c=(unsigned char)src[i];
        dst[i] = (c>=32 && c<127 && c!='\t') ? (char)c : ' ';
        ++i;
    }
    dst[i]=0;
}
static void CL_AndroidPublishLabCvars(void)
{
    cvar_t *cv;
    size_t used=0;
    if (++dwLabCatalogTick%15 != 1) return;
    dwLabCatalogPending[0]=0;
    for (cv=cvar_vars; cv; cv=cv->next) {
        char name[128],cur[256],def[256],lat[256];
        int n;
        DWLabCleanField(name,sizeof(name),cv->name);
        DWLabCleanField(cur,sizeof(cur),cv->string);
        DWLabCleanField(def,sizeof(def),cv->resetString);
        DWLabCleanField(lat,sizeof(lat),cv->latchedString);
        n=snprintf(dwLabCatalogPending+used,DW_LAB_CATALOG_CAP-used,
                   "%s\t%s\t%s\t%d\t%s\n",
                   name,cur,def,cv->flags,lat);
        if (n<0) break;
        if ((size_t)n >= DW_LAB_CATALOG_CAP-used) {
            dwLabCatalogPending[used]=0;
            break;
        }
        used+=(size_t)n;
    }
    pthread_mutex_lock(&dwLabCatalogLock);
    memcpy(dwLabCatalogPublished,dwLabCatalogPending,used+1);
    pthread_mutex_unlock(&dwLabCatalogLock);
}
JNIEXPORT jstring JNICALL
Java_org_darkwolf_rend2_DarkWolfActivity_nativeLabCvars(
    JNIEnv *env, jclass clazz)
{
    jstring result;
    (void)clazz;
    pthread_mutex_lock(&dwLabCatalogLock);
    result=(*env)->NewStringUTF(env,dwLabCatalogPublished);
    pthread_mutex_unlock(&dwLabCatalogLock);
    return result;
}
'''
s=s.replace(needle,catalog+"\n"+bridge+"\n"+ci_scene+"\n"+needle,1)
# Integrate at action consumption, exactly once per frame.
needle2="    androidGameAppliedMask = desired;"
assert needle2 in s
s=s.replace(needle2,needle2+"\n    CL_AndroidConsumeLabCommand();\n    CL_AndroidPublishLabCvars();\n    CL_AndroidCIGameViewGate();",1)
path.write_text(s)
print("GRAPHICS_LAB_JNI_BRIDGE=APPLIED")
