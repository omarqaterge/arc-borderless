#import <Cocoa/Cocoa.h>
#import <CommonCrypto/CommonDigest.h>
#import <unistd.h>

static NSString *fileSHA256(NSString *path) {
 NSFileHandle *file=[NSFileHandle fileHandleForReadingAtPath:path]; if(!file) return nil;
 CC_SHA256_CTX context; CC_SHA256_Init(&context);
 while(YES) { @autoreleasepool {
  NSData *data=[file readDataOfLength:1024*1024]; if(!data.length) break;
  CC_SHA256_Update(&context,data.bytes,(CC_LONG)data.length);
 } }
 [file closeFile]; unsigned char digest[CC_SHA256_DIGEST_LENGTH]; CC_SHA256_Final(digest,&context);
 NSMutableString *result=[NSMutableString stringWithCapacity:CC_SHA256_DIGEST_LENGTH*2];
 for(int index=0;index<CC_SHA256_DIGEST_LENGTH;index++) [result appendFormat:@"%02x",digest[index]];
 return result;
}

static int showAlert(NSString *message,NSString *detail,NSString *button,BOOL cancel) {
 [NSApplication sharedApplication]; NSAlert *alert=[NSAlert new];
 alert.messageText=message; alert.informativeText=detail; [alert addButtonWithTitle:button];
 if(cancel) [alert addButtonWithTitle:@"Cancel"];
 [NSApp activateIgnoringOtherApps:YES]; return (int)[alert runModal];
}

static BOOL quitOfficialArc(void) {
 NSArray *applications=[NSRunningApplication runningApplicationsWithBundleIdentifier:@"company.thebrowser.Browser"];
 if(!applications.count) return YES;
 if(showAlert(@"Arc is already open",@"Arc Borderless uses the signed Arc process, so Arc must close before Borderless mode can start. Your windows and tabs will be restored by Arc.",@"Quit Arc and Continue",YES)!=NSAlertFirstButtonReturn) return NO;
 for(NSRunningApplication *application in applications) [application terminate];
 NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:20];
 while(deadline.timeIntervalSinceNow>0) {
  BOOL running=NO; for(NSRunningApplication *application in applications) if(!application.terminated) running=YES;
  if(!running) return YES;
  [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
 }
 showAlert(@"Arc could not close",@"Quit Arc from its menu, then open Arc Borderless again.",@"OK",NO);
 return NO;
}

int main(int argc,char **argv) { @autoreleasepool {
 NSBundle *bundle=NSBundle.mainBundle;
 NSDictionary *configuration=[NSDictionary dictionaryWithContentsOfFile:[bundle pathForResource:@"Borderless" ofType:@"plist"]];
 if(![configuration[@"mode"] isEqual:@"signed-single-instance"]) {
  showAlert(@"Arc Borderless is damaged",@"Run the installer again to rebuild the launcher.",@"OK",NO); return 70;
 }
 NSString *source=configuration[@"sourceInfo"][@"source"];
 NSDictionary *sourcePlist=[NSDictionary dictionaryWithContentsOfFile:[source stringByAppendingPathComponent:@"Contents/Info.plist"]];
 NSString *binary=[source stringByAppendingPathComponent:[@"Contents/MacOS" stringByAppendingPathComponent:sourcePlist[@"CFBundleExecutable"] ?: @"Arc"]];
 NSString *expected=configuration[@"sourceInfo"][@"sourceSHA256"];
 if(![fileSHA256(binary) isEqual:expected]) {
  showAlert(@"Arc Borderless needs an update",@"Arc has changed since this launcher was installed. Run the Arc Borderless installer again to verify the new Arc build before opening it.",@"OK",NO); return 78;
 }
 NSString *report=nil,*probe=nil; NSMutableArray *arguments=[NSMutableArray array];
 for(int index=1;index<argc;index++) {
  NSString *argument=@(argv[index]);
  if([argument isEqual:@"--borderless-probe-root"] && index+1<argc) probe=@(argv[++index]);
  else if([argument isEqual:@"--borderless-report"] && index+1<argc) report=@(argv[++index]);
  else [arguments addObject:argument];
 }
 if(!probe && !quitOfficialArc()) return 0;
 NSString *library=[bundle.bundlePath stringByAppendingPathComponent:@"Contents/Frameworks/ArcBorderless.dylib"];
 setenv("ARCB_OFFICIAL_MODE","1",1); setenv("DYLD_INSERT_LIBRARIES",library.fileSystemRepresentation,1);
 unsetenv("ARCB_KEYCHAIN_NAMESPACE"); unsetenv("CFFIXED_USER_HOME"); unsetenv("ARCB_VERIFY_ENCRYPTION");
 if(report) setenv("ARCB_REPORT",report.fileSystemRepresentation,1); else unsetenv("ARCB_REPORT");
 if(probe) {
  [arguments insertObject:[@"--user-data-dir=" stringByAppendingString:probe] atIndex:0];
  [arguments addObject:@"--no-first-run"]; [arguments addObject:@"--no-default-browser-check"];
 }
 char **childArguments=calloc(arguments.count+2,sizeof(char*)); childArguments[0]=(char*)binary.fileSystemRepresentation;
 for(NSUInteger index=0;index<arguments.count;index++) childArguments[index+1]=(char*)[arguments[index] UTF8String];
 execv(childArguments[0],childArguments); perror("Arc Borderless launch"); return 71;
}}
