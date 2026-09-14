#import <unistd.h>
#import <Cocoa/Cocoa.h>
#import <QuartzCore/QuartzCore.h>
#import <Security/Security.h>
#import <objc/runtime.h>

static Class findScrimClass(void) {
 unsigned count=0; Class *classes=objc_copyClassList(&count); Class found=Nil;
 for(unsigned i=0;i<count;i++) if(strstr(class_getName(classes[i]),"18ViewWithScrimInset")) { if(found) { free(classes); return Nil; } found=classes[i]; }
 free(classes); return found;
}
#define ARCB_OFFICIAL_BUILD 1
#include "ResizeFix.inc"
#include "FrameFix.inc"
#include "Runtime.inc"
static void (*originalLayout)(NSView*,SEL);
static void borderlessLayout(NSView *v,SEL sel) {
 if(v.superview) borderlessFrame(v,@selector(setFrame:),v.superview.bounds);
 originalLayout(v,sel);
 for(NSView *child in v.subviews) {
  child.frame=v.bounds; child.layer.cornerRadius=0;
  if([NSStringFromClass(child.class) isEqualToString:@"ARCUI.ShadowView"]) child.hidden=YES;
 }
 v.layer.cornerRadius=0;
}
__attribute__((constructor)) static void start(void) {
 unsetenv("DYLD_INSERT_LIBRARIES");
 Class scrim=findScrimClass();
 if(!runtimeCompatible(scrim)) { writeReport(@{@"compatible":@NO,@"hooksInstalled":@NO}); fprintf(stderr,"Unsupported Arc runtime. Refusing to open profile.\n"); _exit(78); }
 installFrames(); installContentLayout(); installPaneOutline(); installResizeAreas();
 Method m=class_getInstanceMethod(scrim,@selector(layout)); originalLayout=(void*)method_getImplementation(m);
 if(!class_addMethod(scrim,@selector(layout),(IMP)borderlessLayout,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)borderlessLayout);
 scheduleReport();
}
