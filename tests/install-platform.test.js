import test from 'node:test';
import assert from 'node:assert/strict';
import {detectPlatform} from '../web/install-platform.js';
test('installation instructions distinguish mobile systems and desktop browsers',()=>{
  for(const [info,expected] of [
    [{userAgent:'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},'windows'],
    [{userAgent:'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)'},'macos'],
    [{userAgent:'Mozilla/5.0 (X11; Linux x86_64)'},'linux'],
    [{userAgent:'Mozilla/5.0 (X11; CrOS x86_64)'},'linux'],
    [{userAgent:'Mozilla/5.0 (Linux; Android 16; Mobile)'},'android'],
    [{userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)'},'ios'],
    [{userAgent:'Mozilla/5.0 (Macintosh; Intel Mac OS X)',platform:'MacIntel',maxTouchPoints:5},'ios'],
    [{userAgent:'Unknown browser'},'other'],
  ])assert.equal(detectPlatform(info),expected);
});
