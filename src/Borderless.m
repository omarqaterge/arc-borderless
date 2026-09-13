#import <unistd.h>
#import <Cocoa/Cocoa.h>
#import <QuartzCore/QuartzCore.h>
#import <CloudKit/CloudKit.h>
#import <objc/runtime.h>
static Class findScrimClass(void) {
 unsigned count=0; Class *classes=objc_copyClassList(&count); Class found=Nil;
 for(unsigned i=0;i<count;i++) if(strstr(class_getName(classes[i]),"18ViewWithScrimInset")) { if(found) { free(classes); return Nil; } found=classes[i]; }
 free(classes); return found;
}
#include "KeychainFix.inc"
#include "ResizeFix.inc"
#include "FrameFix.inc"
#include "Runtime.inc"
static id noCloudContainer(id self,SEL sel,id name) { return nil; }
static id noDefaultCloudContainer(id self,SEL sel) { return nil; }
static void (*originalLayout)(NSView*,SEL);
static void borderlessLayout(NSView *v,SEL sel) {
 if(v.superview) borderlessFrame(v,@selector(setFrame:),v.superview.bounds);
 originalLayout(v,sel);
 for(NSView *child in v.subviews) {
  child.frame=v.bounds;
  child.layer.cornerRadius=0;
  if([NSStringFromClass(child.class) isEqualToString:@"ARCUI.ShadowView"]) child.hidden=YES;
 }
 v.layer.cornerRadius=0;
}
__attribute__((constructor)) static void start(void) {
 unsetenv("DYLD_INSERT_LIBRARIES");
 Class scrim=findScrimClass();
 if(!runtimeCompatible(scrim)) { writeReport(@{@"compatible":@NO,@"hooksInstalled":@NO}); fprintf(stderr,"Unsupported Arc runtime. Refusing to open profile.\n"); _exit(78); }
 installUpdateBlock();
 method_setImplementation(class_getClassMethod(CKContainer.class,@selector(defaultContainer)),(IMP)noDefaultCloudContainer);
 method_setImplementation(class_getClassMethod(CKContainer.class,@selector(containerWithIdentifier:)),(IMP)noCloudContainer);

 installFrames(); installContentLayout(); installPaneOutline(); installResizeAreas();
 Method m=class_getInstanceMethod(scrim,@selector(layout));
 originalLayout=(void*)method_getImplementation(m);
 if(!class_addMethod(scrim,@selector(layout),(IMP)borderlessLayout,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)borderlessLayout);
 scheduleReport();
}
