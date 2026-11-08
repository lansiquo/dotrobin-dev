'use strict';
var target = new URL('sast.html', location.href);
target.search = location.search;
target.hash = location.hash;
location.replace(target.href);
