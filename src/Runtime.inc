static BOOL requireMethod(NSString *name, SEL selector) {
 Class candidate=NSClassFromString(name); Method method=candidate ? class_getInstanceMethod(candidate,selector) : NULL;
 Method base=class_getInstanceMethod(NSView.class,selector);
 return candidate && [candidate isSubclassOfClass:NSView.class] && method && base && !strcmp(method_getTypeEncoding(method),method_getTypeEncoding(base));
}
static void writeReport(NSDictionary *value) {
 const char *path=getenv("ARCB_REPORT"); if(!path) return;
 NSData *data=[NSJSONSerialization dataWithJSONObject:value options:NSJSONWritingPrettyPrinted error:NULL];
 [data writeToFile:@(path) options:NSDataWritingAtomic error:NULL];
}
static BOOL runtimeCompatible(Class scrim) {
 if(!scrim || !class_getInstanceMethod(scrim,@selector(layout))) return NO;
 for(NSString *name in @[@"_TtCC3Arc27WindowContentViewController11ContentView",@"ARCUI.SplitViewContentPaneView",@"ARCUI.DraggingDestinationForwardingView",@"Arc.SplitViewDraggerHandleView",@"Arc.SplitViewBottomDraggerHandleView"])
  if(!requireMethod(name,@selector(layout))) return NO;
 return YES;
}
static void countViews(NSView *view,NSMutableDictionary *counts) {
 NSString *name=NSStringFromClass(view.class);
 if([name containsString:@"FindInPage"] || [name containsString:@"TopBarPanel"] || [name containsString:@"WebContentsViewCocoa"] || [name containsString:@"SplitViewContentPaneView"]) {
  NSString *key=[name stringByAppendingString:view.hidden ? @":hidden" : @":visible"];
  counts[key]=@([counts[key] intValue]+1);
 }
 for(NSView *child in view.subviews) countViews(child,counts);
}
static void scheduleReport(void) {
 if(!getenv("ARCB_REPORT")) return;
 dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_main_queue(),^{
  NSMutableDictionary *counts=[NSMutableDictionary dictionary]; int browserWindows=0;
  for(NSWindow *window in NSApp.windows) {
   if([NSStringFromClass(window.class) isEqual:@"Arc.BrowserWindow"]) browserWindows++;
   if(window.contentView) countViews(window.contentView,counts);
  }
  writeReport(@{@"compatible":@YES,@"hooksInstalled":@YES,@"bundleID":NSBundle.mainBundle.bundleIdentifier ?: @"",@"browserWindows":@(browserWindows),@"windows":@(NSApp.windows.count),@"views":counts,@"officialMode":@YES,@"cloudKitDisabled":@NO,@"sparkleBlocked":@NO});
  scheduleReport();
 });
}
