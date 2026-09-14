#import <Cocoa/Cocoa.h>

int main(int argc,char **argv) { @autoreleasepool {
 if(argc==3 && !strcmp(argv[1],"quit")) {
  NSString *path=[@(argv[2]) stringByResolvingSymlinksInPath];
  for(NSRunningApplication *app in NSWorkspace.sharedWorkspace.runningApplications) {
   if(![[app.bundleURL.path stringByResolvingSymlinksInPath] isEqual:path]) continue;
   if(![app terminate]) return 2;
   NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:20];
   while(!app.terminated && deadline.timeIntervalSinceNow>0)
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
   if(!app.terminated) return 3;
  }
  return 0;
 }
 fprintf(stderr,"Usage: manager quit APP\n"); return 64;
}}
