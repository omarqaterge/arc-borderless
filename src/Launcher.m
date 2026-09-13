#import <Cocoa/Cocoa.h>
#import <unistd.h>
#import <sys/file.h>
#import <sys/stat.h>
#import <fcntl.h>
int main(int argc, char **argv) {
 @autoreleasepool {
  NSBundle *bundle=NSBundle.mainBundle;
  NSDictionary *cfg=[NSDictionary dictionaryWithContentsOfFile:[bundle pathForResource:@"Borderless" ofType:@"plist"]];
  if(!cfg) { fprintf(stderr,"Missing Borderless configuration.\n"); return 70; }
  NSString *root=cfg[@"dataRoot"], *report=nil; BOOL verifyEncryption=NO;
  NSMutableArray *args=[NSMutableArray array];
  for(int i=1;i<argc;i++) {
   NSString *a=@(argv[i]);
   if([a isEqual:@"--borderless-probe-root"] && i+1<argc) root=@(argv[++i]);
   else if([a isEqual:@"--borderless-report"] && i+1<argc) report=@(argv[++i]);
   else if([a isEqual:@"--borderless-verify-encryption"]) verifyEncryption=YES;
   else if([a hasPrefix:@"--user-data-dir"] || [a hasPrefix:@"--browser-subprocess-path"]) { fprintf(stderr,"Profile overrides are not permitted.\n"); return 64; }
   else [args addObject:a];
  }
  if(!root.isAbsolutePath || ![[NSFileManager defaultManager] fileExistsAtPath:[root stringByAppendingPathComponent:@".borderless-profile"]]) { fprintf(stderr,"Profile is not initialized; use the installer.\n"); return 70; }
  NSString *home=[root stringByAppendingPathComponent:@"home"];
  NSString *data=[home stringByAppendingPathComponent:@"Library/Application Support/Arc/User Data"];
  NSString *binary=[bundle.bundlePath stringByAppendingPathComponent:@"Contents/MacOS/ArcOriginal"];
  NSString *lib=[bundle.bundlePath stringByAppendingPathComponent:@"Contents/Frameworks/ArcBorderless.dylib"];
  setenv("CFFIXED_USER_HOME",home.fileSystemRepresentation,1);
  setenv("ARCB_KEYCHAIN_NAMESPACE",[cfg[@"keychainNamespace"] UTF8String],1);
  setenv("DYLD_INSERT_LIBRARIES",lib.fileSystemRepresentation,1);
  if(verifyEncryption && report) setenv("ARCB_VERIFY_ENCRYPTION","1",1); else unsetenv("ARCB_VERIFY_ENCRYPTION");
  if(report) setenv("ARCB_REPORT",report.fileSystemRepresentation,1); else unsetenv("ARCB_REPORT");
  [args insertObject:[@"--user-data-dir=" stringByAppendingString:data] atIndex:0];
  // A single credential that Chromium cannot decrypt must not hide every
  // readable credential. Keep the damaged row for recovery instead of
  // silently deleting it.
  [args addObject:@"--enable-features=SkipUndecryptablePasswords"];
  [args addObject:@"--disable-features=ClearUndecryptablePasswords,ClearUndecryptablePasswordsInSync"];
  [args addObject:@"--no-first-run"];
  [args addObject:@"--no-default-browser-check"];
  char **av=calloc(args.count+2,sizeof(char*)); av[0]=(char*)binary.fileSystemRepresentation;
  for(NSUInteger i=0;i<args.count;i++) av[i+1]=(char*)[args[i] UTF8String];
  execv(av[0],av); perror("Arc Borderless launch"); return 71;
 }
}
