// Credential validation executes inside the clone's authorized executable.
static NSDictionary *query(NSString *service) {
 return @{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,(__bridge id)kSecAttrService:service,(__bridge id)kSecUseDataProtectionKeychain:@NO,(__bridge id)kSecReturnAttributes:@YES,(__bridge id)kSecReturnData:@YES,(__bridge id)kSecUseAuthenticationUI:(__bridge id)kSecUseAuthenticationUIFail};
}
#include "VerifyCookies.inc"
static BOOL verifyProfileEncryption(void) {
 NSString *data=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/Arc/User Data"];
 NSString *service=[keyPrefix() stringByAppendingString:@"Arc Safe Storage"];
 for(NSString *profile in [[NSFileManager defaultManager] contentsOfDirectoryAtPath:data error:NULL]) {
  NSString *dir=[data stringByAppendingPathComponent:profile];
  for(NSString *relative in @[@"Cookies",@"Network/Cookies",@"Login Data"]) {
   NSString *file=[dir stringByAppendingPathComponent:relative];
   if([[NSFileManager defaultManager] fileExistsAtPath:file] && verifyEncrypted(service,file,[relative isEqual:@"Login Data"])!=0) return NO;
  }
 }
 return YES;
}
// Runtime checks run before installing any UI hooks. Diagnostics contain no URLs or text.
static BOOL requireMethod(NSString *name, SEL selector) {
 Class c=NSClassFromString(name); Method m=c ? class_getInstanceMethod(c,selector) : NULL;
 Method base=class_getInstanceMethod(NSView.class,selector);
 return c && [c isSubclassOfClass:NSView.class] && m && base && !strcmp(method_getTypeEncoding(m),method_getTypeEncoding(base));
}
static void writeReport(NSDictionary *value) {
 const char *path=getenv("ARCB_REPORT"); if(!path) return;
 NSData *data=[NSJSONSerialization dataWithJSONObject:value options:NSJSONWritingPrettyPrinted error:NULL];
 [data writeToFile:@(path) options:NSDataWritingAtomic error:NULL];
}
static BOOL runtimeCompatible(Class scrim) {
 if(!scrim || !class_getInstanceMethod(scrim,@selector(layout))) return NO;
 for(NSString *s in @[@"_TtCC3Arc27WindowContentViewController11ContentView",@"ARCUI.SplitViewContentPaneView",@"ARCUI.DraggingDestinationForwardingView",@"Arc.SplitViewDraggerHandleView",@"Arc.SplitViewBottomDraggerHandleView"]) if(!requireMethod(s,@selector(layout))) return NO;
 return class_getClassMethod(CKContainer.class,@selector(defaultContainer)) && class_getClassMethod(CKContainer.class,@selector(containerWithIdentifier:));
}
static void disabledUpdate(id self,SEL sel,id sender) {}
static BOOL disabledStart(id self,SEL sel,NSError **error) { return NO; }
static void installUpdateBlock(void) {
 // Block both scheduled and manually requested Sparkle update paths in the clone.
 for(NSString *name in @[@"SUUpdater",@"SPUUpdater",@"SPUStandardUpdaterController"]) {
  Class c=NSClassFromString(name); if(!c) continue;
  for(NSString *s in @[@"checkForUpdates:",@"checkForUpdatesInBackground",@"checkForUpdateInformation",@"startUpdater"]){
   SEL sel=NSSelectorFromString(s); Method m=class_getInstanceMethod(c,sel);
   if(m) { if(!class_addMethod(c,sel,(IMP)disabledUpdate,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)disabledUpdate); }
  }
  Method m=class_getInstanceMethod(c,NSSelectorFromString(@"startUpdater:"));
  if(m) { if(!class_addMethod(c,NSSelectorFromString(@"startUpdater:"),(IMP)disabledStart,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)disabledStart); }
 }
}
static void countViews(NSView *v,NSMutableDictionary *counts) {
 NSString *name=NSStringFromClass(v.class);
 if([name containsString:@"FindInPage"] || [name containsString:@"TopBarPanel"] || [name containsString:@"WebContentsViewCocoa"] || [name containsString:@"SplitViewContentPaneView"]) {
  NSString *key=[name stringByAppendingString:v.hidden ? @":hidden" : @":visible"];
  counts[key]=@([counts[key] intValue]+1);
 }
 for(NSView *child in v.subviews) countViews(child,counts);
}
static void scheduleReport(void) {
 if(!getenv("ARCB_REPORT")) return;
 dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_main_queue(),^{
  NSMutableDictionary *counts=[NSMutableDictionary dictionary];
  int browserWindows=0;
  for(NSWindow *w in NSApp.windows) {
   if([NSStringFromClass(w.class) isEqual:@"Arc.BrowserWindow"]) browserWindows++;
   if(w.contentView) countViews(w.contentView,counts);
  }
  BOOL encryptionVerified=getenv("ARCB_VERIFY_ENCRYPTION") ? verifyProfileEncryption() : NO;
  writeReport(@{@"encryptionVerified":@(encryptionVerified),@"compatible":@YES,@"hooksInstalled":@YES,@"home":NSHomeDirectory(),@"bundleID":NSBundle.mainBundle.bundleIdentifier ?: @"",@"browserWindows":@(browserWindows),@"windows":@(NSApp.windows.count),@"views":counts,@"cloudKitDisabled":@YES,@"sparkleBlocked":@YES});
  scheduleReport();
 });
}
