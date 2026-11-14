import {parseHTML} from 'linkedom';
import vm from 'node:vm';
import fs from 'node:fs/promises';
import {testManager} from './manager.test.mjs';
const script=await fs.readFile(new URL('../work/manager-bundled.js',import.meta.url),'utf8');
console.log(testManager({parseHTML,vm,script}));
