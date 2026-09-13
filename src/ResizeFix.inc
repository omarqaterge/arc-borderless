static void clearHandleVisuals(NSView *handle) {
 handle.layer.backgroundColor = nil;
 handle.layer.borderWidth = 0;
 handle.layer.borderColor = nil;
 for(CALayer *sub in handle.layer.sublayers) {
  sub.hidden = YES;
 }
 for(NSView *child in handle.subviews) {
  child.hidden = YES;
  child.alphaValue = 0;
 }
}

static void handleUpdateLayerFixed(NSView *v, SEL sel) {
 clearHandleVisuals(v);
}

static void handleDrawRectFixed(NSView *v, SEL sel, NSRect r) {
 // Completely transparent
}

static void syncResizeAreas(NSView *parent) {
 static BOOL syncing=NO;
 if(syncing || ![NSStringFromClass(parent.class) isEqualToString:@"ARCUI.DraggingDestinationForwardingView"]) return;
 syncing=YES;
 for(NSView *handle in [parent.subviews copy]) {
  NSString *name=NSStringFromClass(handle.class);
  BOOL vertical=[name isEqualToString:@"Arc.SplitViewDraggerHandleView"];
  BOOL horizontal=[name isEqualToString:@"Arc.SplitViewBottomDraggerHandleView"];
  if(!vertical && !horizontal) continue;
  if(handle.hidden) continue;
  clearHandleVisuals(handle);
  [parent addSubview:handle positioned:NSWindowAbove relativeTo:nil];
 }
 syncing=NO;
}
static void (*outerLayoutOriginal)(NSView*,SEL);
static void outerLayoutFixed(NSView *v,SEL sel) { outerLayoutOriginal(v,sel); syncResizeAreas(v); }
static void (*nativeHandleSetFrame)(NSView*,SEL,NSRect);
static void handleFrameFixed(NSView *v,SEL sel,NSRect r) {
 NSView *p=v.superview;
 if(p) {
  if([NSStringFromClass(v.class) isEqualToString:@"Arc.SplitViewDraggerHandleView"]) {
   if(NSMaxX(r)<NSMaxX(p.bounds)-0.5) r.origin.x+=r.size.width/2;
  }
  else if([NSStringFromClass(v.class) isEqualToString:@"Arc.SplitViewBottomDraggerHandleView"]) {
   if(NSMinY(r)>NSMinY(p.bounds)+0.5) r.origin.y-=r.size.height/2;
   r.size.width = NSWidth(p.bounds);
  }
 }
 nativeHandleSetFrame(v,sel,r);
 clearHandleVisuals(v);
}
static void installResizeAreas(void) {
 Class c=NSClassFromString(@"ARCUI.DraggingDestinationForwardingView");
 Method m=class_getInstanceMethod(c,@selector(layout));
 outerLayoutOriginal=(void*)method_getImplementation(m);
 if(!class_addMethod(c,@selector(layout),(IMP)outerLayoutFixed,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)outerLayoutFixed);
 nativeHandleSetFrame=(void*)class_getMethodImplementation(NSView.class,@selector(setFrame:));
 for(NSString *name in @[@"Arc.SplitViewDraggerHandleView",@"Arc.SplitViewBottomDraggerHandleView"]) {
  Class hc = NSClassFromString(name);
  if(!hc) continue;
  class_addMethod(hc,@selector(setFrame:),(IMP)handleFrameFixed,method_getTypeEncoding(class_getInstanceMethod(NSView.class,@selector(setFrame:))));
  Method ul = class_getInstanceMethod(hc, @selector(updateLayer));
  if(ul) { if(!class_addMethod(hc,@selector(updateLayer),(IMP)handleUpdateLayerFixed,method_getTypeEncoding(ul))) method_setImplementation(ul,(IMP)handleUpdateLayerFixed); }
  else class_addMethod(hc, @selector(updateLayer), (IMP)handleUpdateLayerFixed, "v@:");
  Method dr = class_getInstanceMethod(hc, @selector(drawRect:));
  if(dr) { if(!class_addMethod(hc,@selector(drawRect:),(IMP)handleDrawRectFixed,method_getTypeEncoding(dr))) method_setImplementation(dr,(IMP)handleDrawRectFixed); }
  else class_addMethod(hc, @selector(drawRect:), (IMP)handleDrawRectFixed, "v@:{CGRect={CGPoint=dd}{CGSize=dd}}");
 }
}
