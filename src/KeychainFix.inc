#import <Security/Security.h>
static NSString *keyPrefix(void) {
 const char *s=getenv("ARCB_KEYCHAIN_NAMESPACE");
 return s ? @(s) : @"ArcBorderless/Unconfigured/";
}
static NSDictionary *localQuery(CFDictionaryRef query) {
 NSMutableDictionary *q=[(__bridge NSDictionary*)query mutableCopy];
 if([q[(__bridge id)kSecClass] isEqual:(__bridge id)kSecClassGenericPassword] && q[(__bridge id)kSecAttrService]) {
  q[(__bridge id)kSecAttrService]=[keyPrefix() stringByAppendingString:q[(__bridge id)kSecAttrService]];
  [q removeObjectForKey:(__bridge id)kSecAttrAccessGroup];
  [q removeObjectForKey:(__bridge id)kSecAttrSynchronizable];
  q[(__bridge id)kSecUseDataProtectionKeychain]=@NO;
 }
 return q;
}
static OSStatus localAdd(CFDictionaryRef q, CFTypeRef *r) { return SecItemAdd((__bridge CFDictionaryRef)localQuery(q),r); }
static OSStatus localCopy(CFDictionaryRef q, CFTypeRef *r) { return SecItemCopyMatching((__bridge CFDictionaryRef)localQuery(q),r); }
static OSStatus localUpdate(CFDictionaryRef q, CFDictionaryRef a) { return SecItemUpdate((__bridge CFDictionaryRef)localQuery(q),a); }
static OSStatus localDelete(CFDictionaryRef q) { return SecItemDelete((__bridge CFDictionaryRef)localQuery(q)); }
// Chromium versions using the legacy API must resolve to the same isolated key.
static OSStatus localFind(CFTypeRef kc, UInt32 sl, const char *s, UInt32 al, const char *a, UInt32 *pl, void **p, SecKeychainItemRef *i) {
 NSString *svc=[[NSString alloc] initWithBytes:s length:sl encoding:NSUTF8StringEncoding];
 NSData *mapped=[[keyPrefix() stringByAppendingString:svc] dataUsingEncoding:NSUTF8StringEncoding];
 return SecKeychainFindGenericPassword(kc,(UInt32)mapped.length,mapped.bytes,al,a,pl,p,i);
}
static OSStatus localLegacyAdd(SecKeychainRef kc, UInt32 sl, const char *s, UInt32 al, const char *a, UInt32 pl, const void *p, SecKeychainItemRef *i) {
 NSString *svc=[[NSString alloc] initWithBytes:s length:sl encoding:NSUTF8StringEncoding];
 NSData *mapped=[[keyPrefix() stringByAppendingString:svc] dataUsingEncoding:NSUTF8StringEncoding];
 return SecKeychainAddGenericPassword(kc,(UInt32)mapped.length,mapped.bytes,al,a,pl,p,i);
}
#define INTERPOSE(repl,orig) __attribute__((used)) static struct { const void *replacement; const void *replacee; } interpose_##orig __attribute__((section("__DATA,__interpose"))) = {(void*)repl,(void*)orig};
INTERPOSE(localAdd,SecItemAdd)
INTERPOSE(localCopy,SecItemCopyMatching)
INTERPOSE(localUpdate,SecItemUpdate)
INTERPOSE(localDelete,SecItemDelete)
INTERPOSE(localFind,SecKeychainFindGenericPassword)
INTERPOSE(localLegacyAdd,SecKeychainAddGenericPassword)
