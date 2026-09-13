#import <sqlite3.h>
#import <CommonCrypto/CommonCrypto.h>
static int verifyEncrypted(NSString *service, NSString *path, BOOL passwords) {
 CFTypeRef raw=NULL; OSStatus s=SecItemCopyMatching((__bridge CFDictionaryRef)query(service),&raw);
 if(s!=errSecSuccess) { fprintf(stderr,"Cannot access verification key (%d).\n",(int)s); return 4; }
 NSDictionary *item=CFBridgingRelease(raw); NSData *password=item[(__bridge id)kSecValueData];
 unsigned char key[16];
 if(CCKeyDerivationPBKDF(kCCPBKDF2,password.bytes,password.length,(const unsigned char*)"saltysalt",9,kCCPRFHmacAlgSHA1,1003,key,16)!=kCCSuccess) return 10;
 sqlite3 *db=NULL;
 if(sqlite3_open_v2(path.fileSystemRepresentation,&db,SQLITE_OPEN_READONLY,NULL)!=SQLITE_OK) { if(db) sqlite3_close(db); return 11; }
 sqlite3_stmt *stmt=NULL; int version=0;
 if(sqlite3_prepare_v2(db,"SELECT value FROM meta WHERE key='version'",-1,&stmt,NULL)==SQLITE_OK && sqlite3_step(stmt)==SQLITE_ROW) version=sqlite3_column_int(stmt,0);
 sqlite3_finalize(stmt);
 if(sqlite3_prepare_v2(db,passwords ? "SELECT origin_url,password_value FROM logins WHERE length(password_value)>0" : "SELECT host_key,encrypted_value FROM cookies WHERE length(encrypted_value)>0",-1,&stmt,NULL)!=SQLITE_OK) { sqlite3_close(db); return 12; }
 int verified=0,failed=0,unsupported=0;
 while(sqlite3_step(stmt)==SQLITE_ROW) {
  const unsigned char *encrypted=sqlite3_column_blob(stmt,1); int length=sqlite3_column_bytes(stmt,1);
  if(length<3 || memcmp(encrypted,"v10",3)) { unsupported++; continue; }
  NSMutableData *clear=[NSMutableData dataWithLength:length+16]; size_t count=0;
  CCCryptorStatus status=CCCrypt(kCCDecrypt,kCCAlgorithmAES,kCCOptionPKCS7Padding,key,16,"                ",encrypted+3,length-3,clear.mutableBytes,clear.length,&count);
  BOOL ok=status==kCCSuccess;
  if(ok && !passwords && version>=24) {
   const char *host=(const char*)sqlite3_column_text(stmt,0); unsigned char digest[CC_SHA256_DIGEST_LENGTH];
   CC_SHA256(host,(CC_LONG)strlen(host),digest);
   ok=count>=32 && !memcmp(clear.bytes,digest,32);
  }
  if(ok) verified++; else failed++;
  memset(clear.mutableBytes,0,clear.length);
 }
 sqlite3_finalize(stmt); sqlite3_close(db); memset(key,0,sizeof(key));
 printf("{\"verified\":%d,\"failed\":%d,\"unsupported\":%d,\"schema\":%d}\n",verified,failed,unsupported,version);
 return failed || unsupported ? 13 : 0;
}
