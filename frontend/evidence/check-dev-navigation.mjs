import {chromium} from '@playwright/test'
import {writeFile} from 'node:fs/promises'
const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>sessionStorage.setItem('nav-boot-count',String(Number(sessionStorage.getItem('nav-boot-count')||0)+1)))
try{
 await page.goto('http://127.0.0.1:5179/tablet');await page.getByRole('button',{name:'模拟手机扫码',exact:true}).waitFor({timeout:30000});const before=await page.evaluate(()=>Number(sessionStorage.getItem('nav-boot-count')))
 await page.getByRole('link',{name:'员工手机端',exact:true}).click();await page.getByRole('button',{name:'模拟企业微信登录',exact:true}).click();await page.waitForURL('**/employee');await page.getByRole('button',{name:/报价与交付协调/}).click();await page.getByRole('button',{name:'主动更正',exact:true}).waitFor();
 await page.getByRole('link',{name:'管理后台',exact:true}).click();await page.getByRole('button',{name:'进入演示管理员',exact:true}).click();await page.waitForURL('**/admin/overview');await page.getByRole('menuitem',{name:'组织部门',exact:true}).click();await page.getByRole('button',{name:'模拟同步组织'}).waitFor();await page.getByRole('link',{name:'组件与状态',exact:true}).click();await page.getByRole('button',{name:'验证表单',exact:true}).waitFor();
 const after=await page.evaluate(()=>Number(sessionStorage.getItem('nav-boot-count')));const result={scope:'dev-mode navigation only',before,after,noReload:before===after,errors};await writeFile('evidence/dev-navigation-result.json',JSON.stringify(result,null,2));console.log(result);if(before!==after||errors.length)process.exitCode=1
}finally{await browser.close()}
