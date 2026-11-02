// Detection only recommends instructions; install capability comes from the browser.
export function detectPlatform({userAgent='',platform='',maxTouchPoints=0}={}){
  if(/iPhone|iPad|iPod/i.test(userAgent)||(/Mac/i.test(platform)&&maxTouchPoints>1))return 'ios';
  if(/Android/i.test(userAgent))return 'android';
  if(/Windows/i.test(userAgent))return 'windows';
  if(/Macintosh|Mac OS X/i.test(userAgent)||/Mac/i.test(platform))return 'macos';
  if(/Linux|CrOS/i.test(userAgent))return 'linux';
  return 'other';
}
export const platformNames={windows:'Windows',macos:'macOS',linux:'Linux ou ChromeOS',android:'Android',ios:'iPhone ou iPad',other:'seu aparelho'};
