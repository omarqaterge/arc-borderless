static BOOL singlePane(NSView *parent) {
 NSUInteger n=0;
 for(NSView *v in parent.subviews) if([NSStringFromClass(v.class) isEqualToString:@"ARCUI.SplitViewContentPaneView"]) n++;
 return n>=1;
}

static char noBorderLayerKey;

static void tagNoBorder(CALayer *layer) {
 if(!layer) return;
 objc_setAssociatedObject(layer, &noBorderLayerKey, @YES, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
 layer.borderWidth = 0;
 layer.borderColor = nil;
 if([layer isKindOfClass:CAShapeLayer.class]) {
  CAShapeLayer *sl = (CAShapeLayer*)layer;
  sl.strokeColor = nil;
  sl.lineWidth = 0;
 }
 for(CALayer *sub in layer.sublayers) tagNoBorder(sub);
}

static BOOL isFindInPageView(NSView *v) {
 NSView *cur = v;
 while(cur) {
  if([NSStringFromClass(cur.class) containsString:@"FindInPage"]) return YES;
  cur = cur.superview;
 }
 return NO;
}

static void tagViewNoBorder(NSView *v) {
 if(!v || isFindInPageView(v)) return;
 if(v.layer) tagNoBorder(v.layer);
 for(NSView *child in v.subviews) tagViewNoBorder(child);
}

static BOOL isSplitOrBorderlessLayer(CALayer *layer) {
 if(!layer) return NO;
 id del = layer.delegate;
 if(del && [del isKindOfClass:NSView.class] && isFindInPageView((NSView*)del)) return NO;
 if(objc_getAssociatedObject(layer, &noBorderLayerKey)) return YES;
 CALayer *cur = layer;
 while(cur) {
  id cdel = cur.delegate;
  if(cdel && [cdel isKindOfClass:NSView.class]) {
   if(isFindInPageView((NSView*)cdel)) return NO;
  }
  if(objc_getAssociatedObject(cur, &noBorderLayerKey)) {
   objc_setAssociatedObject(layer, &noBorderLayerKey, @YES, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
   return YES;
  }
  if(cdel && [cdel isKindOfClass:NSView.class]) {
   NSView *v = (NSView*)cdel;
   NSString *cname = NSStringFromClass(v.class);
   if([cname containsString:@"SplitView"] || [cname containsString:@"ViewWithScrimInset"] || [cname containsString:@"DraggerHandle"]) {
    objc_setAssociatedObject(layer, &noBorderLayerKey, @YES, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    return YES;
   }
  }
  cur = cur.superlayer;
 }
 return NO;
}

static void (*shapeStrokeOriginal)(CAShapeLayer*,SEL,CGColorRef);
static void shapeStrokeFixed(CAShapeLayer *layer,SEL sel,CGColorRef color) {
 if(isSplitOrBorderlessLayer(layer) || objc_getAssociatedObject(layer.superlayer,&noBorderLayerKey)) color=nil;
 shapeStrokeOriginal(layer,sel,color);
}
static void (*borderWidthOriginal)(CALayer*,SEL,CGFloat);
static void borderWidthFixed(CALayer *layer,SEL sel,CGFloat width) {
 if(isSplitOrBorderlessLayer(layer)) width=0;
 borderWidthOriginal(layer,sel,width);
}
static void (*borderColorOriginal)(CALayer*,SEL,CGColorRef);
static void borderColorFixed(CALayer *layer,SEL sel,CGColorRef color) {
 if(isSplitOrBorderlessLayer(layer)) color=nil;
 borderColorOriginal(layer,sel,color);
}
static void (*lineWidthOriginal)(CAShapeLayer*,SEL,CGFloat);
static void lineWidthFixed(CAShapeLayer *layer,SEL sel,CGFloat width) {
 if(isSplitOrBorderlessLayer(layer) || objc_getAssociatedObject(layer.superlayer,&noBorderLayerKey)) width=0;
 lineWidthOriginal(layer,sel,width);
}
static void (*addSublayerOriginal)(CALayer*,SEL,CALayer*);
static void addSublayerFixed(CALayer *layer,SEL sel,CALayer *sublayer) {
 if(isSplitOrBorderlessLayer(layer)) {
  tagNoBorder(sublayer);
 }
 addSublayerOriginal(layer,sel,sublayer);
}

static BOOL isSplitPane(NSView *v) {
 NSView *cur = v;
 while(cur) {
  if([NSStringFromClass(cur.class) isEqualToString:@"ARCUI.SplitViewContentPaneView"]) return YES;
  cur = cur.superview;
 }
 return NO;
}

static void (*paneLayoutOriginal)(NSView*,SEL);
static void paneLayoutFixed(NSView *v,SEL sel) {
 paneLayoutOriginal(v,sel);
 syncResizeAreas(v.superview);
 tagViewNoBorder(v);
}

static BOOL isSplitToolbarOrGrabber(NSView *v) {
 if(!v) return NO;
 NSString *name = NSStringFromClass(v.class);
 if([name containsString:@"FindInPage"]) return NO;
 if([name containsString:@"TopBar"] || [name containsString:@"WindowContentGrabber"] || [name containsString:@"TouchTransparentView"]) return YES;
 if([name isEqualToString:@"ARCUI.FlippedView"]) {
  if(v.subviews.count == 0) return YES;
  for(NSView *child in v.subviews) {
   NSString *cname = NSStringFromClass(child.class);
   if([cname containsString:@"TopBarPanelView"] || [cname containsString:@"TopBar"] || [cname containsString:@"Grabber"]) return YES;
  }
 }
 return NO;
}

static void (*baseSetFrame)(NSView*,SEL,NSRect);
static void borderlessFrame(NSView *v,SEL sel,NSRect frame) {
 NSString *name=NSStringFromClass(v.class);
 NSView *parent=v.superview;
 if(parent && [NSStringFromClass(v.window.class) isEqualToString:@"Arc.BrowserWindow"]) {
  if([name containsString:@"ViewWithScrimInset"] || [name containsString:@"WindowContentViewController11ContentView"]) frame=parent.bounds;
  else if([name isEqualToString:@"ARCUI.SplitViewContentPaneView"] && singlePane(parent)) {
   // Arc reserves a ten-point drag gutter on the right and bottom of every pane.
   CGFloat bottom=MIN(10,MAX(0,frame.origin.y-NSMinY(parent.bounds)));
   frame.origin.y-=bottom;
   frame.size.height+=bottom;
   frame.size.width=MIN(frame.size.width+10,NSMaxX(parent.bounds)-frame.origin.x);
   frame.size.height=MIN(frame.size.height+10,NSMaxY(parent.bounds)-frame.origin.y);
  }
  else if([name isEqualToString:@"ARCUI.DraggingDestinationForwardingView"] && singlePane(v) && frame.origin.x<=16 && NSHeight(frame)>NSHeight(parent.bounds)-20) frame=parent.bounds;
  else if([NSStringFromClass(parent.class) containsString:@"WindowContentViewController11ContentView"]) {
   if([name isEqualToString:@"NSView"]) {
    if(isSplitPane(parent)) {
     frame = parent.bounds;
    } else {
     CGFloat avail=NSHeight(parent.bounds)-frame.origin.y;
     if(avail>frame.size.height) frame.size.height=avail;
     frame.size.width=NSWidth(parent.bounds);
    }
   } else if(isSplitToolbarOrGrabber(v)) {
    v.hidden = YES;
    frame = NSZeroRect;
   }
  }
  else if([name containsString:@"WebContentViewControllerSplitView"]) {
   if(parent) frame = parent.bounds;
  }
 }
 baseSetFrame(v,sel,frame);
}

static void installFrames(void) {
 Method setFrameMethod=class_getInstanceMethod(NSView.class,@selector(setFrame:));
 baseSetFrame=(void*)method_setImplementation(setFrameMethod,(IMP)borderlessFrame);
}

static void (*nativeSetHidden)(NSView*,SEL,BOOL);
static void splitTopBarSetHidden(NSView *v, SEL sel, BOOL hidden) {
 if(isSplitPane(v) && isSplitToolbarOrGrabber(v)) {
  hidden = YES;
 }
 nativeSetHidden(v, sel, hidden);
 if(!hidden && [NSStringFromClass(v.class) containsString:@"FindInPage"]) {
  if(v.superview) [v.superview addSubview:v positioned:NSWindowAbove relativeTo:nil];
  if(v.layer) v.layer.zPosition = 1000;
 }
}

static void (*contentLayoutOriginal)(NSView*,SEL);
static void contentLayoutFixed(NSView *v,SEL sel) {
 contentLayoutOriginal(v,sel);
 BOOL split = isSplitPane(v);
 for(NSView *child in v.subviews) {
  NSString *name=NSStringFromClass(child.class);
  if([name isEqualToString:@"NSView"]) {
   if(split) {
    baseSetFrame(child,@selector(setFrame:),v.bounds);
    for(NSView *sub in child.subviews) {
     if([NSStringFromClass(sub.class) containsString:@"WebContentViewControllerSplitView"]) {
      baseSetFrame(sub,@selector(setFrame:),child.bounds);
     }
    }
   } else {
    NSRect r=child.frame;
    CGFloat avail=NSHeight(v.bounds)-r.origin.y;
    if(avail>r.size.height) r.size.height=avail;
    r.size.width=NSWidth(v.bounds);
    baseSetFrame(child,@selector(setFrame:),r);
   }
  } else if([name containsString:@"FindInPage"]) {
   if(!child.hidden) {
    [v addSubview:child positioned:NSWindowAbove relativeTo:nil];
    if(child.layer) child.layer.zPosition = 1000;
   }
  } else if(isSplitToolbarOrGrabber(child)) {
   child.hidden = YES;
   baseSetFrame(child,@selector(setFrame:),NSZeroRect);
  }
 }
}

static void installContentLayout(void) {
 Class c=NSClassFromString(@"_TtCC3Arc27WindowContentViewController11ContentView");
 Method m=class_getInstanceMethod(c,@selector(layout));
 contentLayoutOriginal=(void*)method_getImplementation(m);
 if(!class_addMethod(c,@selector(layout),(IMP)contentLayoutFixed,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)contentLayoutFixed);
 nativeSetHidden=(void*)method_setImplementation(class_getInstanceMethod(NSView.class,@selector(setHidden:)),(IMP)splitTopBarSetHidden);
}

static void installPaneOutline(void) {
 borderWidthOriginal=(void*)method_setImplementation(class_getInstanceMethod(CALayer.class,@selector(setBorderWidth:)),(IMP)borderWidthFixed);
 borderColorOriginal=(void*)method_setImplementation(class_getInstanceMethod(CALayer.class,@selector(setBorderColor:)),(IMP)borderColorFixed);
 lineWidthOriginal=(void*)method_setImplementation(class_getInstanceMethod(CAShapeLayer.class,@selector(setLineWidth:)),(IMP)lineWidthFixed);
 shapeStrokeOriginal=(void*)method_setImplementation(class_getInstanceMethod(CAShapeLayer.class,@selector(setStrokeColor:)),(IMP)shapeStrokeFixed);
 addSublayerOriginal=(void*)method_setImplementation(class_getInstanceMethod(CALayer.class,@selector(addSublayer:)),(IMP)addSublayerFixed);
 Class c=NSClassFromString(@"ARCUI.SplitViewContentPaneView");
 Method m=class_getInstanceMethod(c,@selector(layout));
 paneLayoutOriginal=(void*)method_getImplementation(m);
 if(!class_addMethod(c,@selector(layout),(IMP)paneLayoutFixed,method_getTypeEncoding(m))) method_setImplementation(m,(IMP)paneLayoutFixed);
}
