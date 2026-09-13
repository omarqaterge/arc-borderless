#import <Cocoa/Cocoa.h>
#import <Security/Security.h>
#import <signal.h>
static NSDictionary *query(NSString *service) {
 return @{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,(__bridge id)kSecAttrService:service,(__bridge id)kSecUseDataProtectionKeychain:@NO,(__bridge id)kSecReturnAttributes:@YES,(__bridge id)kSecReturnData:@YES};
}
static int copyItem(NSString *source,NSString *dest,NSString *app,NSString *account) {
 if(![dest hasPrefix:@"ArcBorderless/"] || [source isEqual:dest]) return 64;
 NSMutableDictionary *q=[query(source) mutableCopy];
 if(account) q[(__bridge id)kSecAttrAccount]=account;
 CFTypeRef raw=NULL; OSStatus s=SecItemCopyMatching((__bridge CFDictionaryRef)q,&raw);
 if(s!=errSecSuccess) { fprintf(stderr,"Source Keychain access failed (%d).\n",(int)s); return 4; }
 NSDictionary *item=CFBridgingRelease(raw); NSData *secret=item[(__bridge id)kSecValueData];
 q[(__bridge id)kSecAttrService]=dest;
 raw=NULL; s=SecItemCopyMatching((__bridge CFDictionaryRef)q,&raw);
 if(s==errSecSuccess) {
  NSDictionary *existing=CFBridgingRelease(raw);
  if(![secret isEqual:existing[(__bridge id)kSecValueData]]) { fprintf(stderr,"Destination has a different value; refusing overwrite.\n"); return 5; }
  return 0;
 }
 if(s!=errSecItemNotFound) { fprintf(stderr,"Destination Keychain access failed (%d).\n",(int)s); return 6; }
 NSMutableArray *trusted=[NSMutableArray array];
 for(NSString *path in @[app,[app stringByAppendingPathComponent:@"Contents/MacOS/ArcOriginal"],NSBundle.mainBundle.executablePath]) {
  SecTrustedApplicationRef t=NULL;
  if(SecTrustedApplicationCreateFromPath(path.fileSystemRepresentation,&t)!=errSecSuccess) return 7;
  [trusted addObject:CFBridgingRelease(t)];
 }
 SecAccessRef access=NULL;
 if(SecAccessCreate(CFSTR("Arc Borderless migrated credential"),(__bridge CFArrayRef)trusted,&access)!=errSecSuccess) return 8;
 NSDictionary *add=@{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,(__bridge id)kSecAttrService:dest,(__bridge id)kSecAttrAccount:item[(__bridge id)kSecAttrAccount] ?: @"Arc",(__bridge id)kSecValueData:secret,(__bridge id)kSecAttrAccess:(__bridge id)access,(__bridge id)kSecUseDataProtectionKeychain:@NO};
 s=SecItemAdd((__bridge CFDictionaryRef)add,NULL); CFRelease(access);
 if(s!=errSecSuccess) { fprintf(stderr,"Could not create isolated credential (%d).\n",(int)s); return 9; }
 return 0;
}
int main(int argc,char **argv) { @autoreleasepool {
 if(argc==3 && !strcmp(argv[1],"assert-id-idle")) {
  NSArray *apps=[NSRunningApplication runningApplicationsWithBundleIdentifier:@(argv[2])];
  if(apps.count) { fprintf(stderr,"Another copy of this clone is running. Quit it before validation.\n"); return 14; }
  return 0;
 }
 if(argc==3 && !strcmp(argv[1],"quit")) {
  NSString *path=[@(argv[2]) stringByResolvingSymlinksInPath];
  for(NSRunningApplication *a in NSWorkspace.sharedWorkspace.runningApplications) if([[a.bundleURL.path stringByResolvingSymlinksInPath] isEqual:path]) {
   if(![a terminate]) return 2;
   NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:20];
   while(!a.terminated && deadline.timeIntervalSinceNow>0) [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
   if(!a.terminated) return 3;
  }
  return 0;
 }
 if(argc==5 && !strcmp(argv[1],"migrate-key")) {
  int result=copyItem(@(argv[2]),@(argv[3]),@(argv[4]),nil);
  if(!result) puts("Isolated encryption key ready; no credentials exported.");
  return result;
 }
 if(argc==5 && !strcmp(argv[1],"migrate-test-auth")) {
  NSString *prefix=@(argv[2]),*dest=@(argv[3]),*app=@(argv[4]);
  // Only the explicitly documented prototype namespace is supported.
  if(![prefix isEqual:@"ArcBorderlessTest/"] || ![dest hasPrefix:@"ArcBorderless/"]) return 64;
  NSDictionary *q=@{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,(__bridge id)kSecUseDataProtectionKeychain:@NO,(__bridge id)kSecReturnAttributes:@YES,(__bridge id)kSecMatchLimit:(__bridge id)kSecMatchLimitAll};
  CFTypeRef raw=NULL; OSStatus s=SecItemCopyMatching((__bridge CFDictionaryRef)q,&raw);
  if(s!=errSecSuccess) return 4;
  NSArray *items=CFBridgingRelease(raw); int count=0;
  for(NSDictionary *item in items) {
   NSString *service=item[(__bridge id)kSecAttrService];
   if(![service hasPrefix:prefix] || [service isEqual:[prefix stringByAppendingString:@"Arc Safe Storage"]]) continue;
   int r=copyItem(service,[dest stringByAppendingString:[service substringFromIndex:prefix.length]],app,item[(__bridge id)kSecAttrAccount]);
   if(r) return r;
   count++;
  }
  printf("Copied %d prototype authentication items within Keychain.\n",count); return 0;
 }
 fprintf(stderr,"Usage: manager quit APP | migrate-key SOURCE_SERVICE DEST_SERVICE APP | migrate-test-auth ArcBorderlessTest/ DEST_PREFIX APP\n"); return 64;
}}
