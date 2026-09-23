import {test,expect} from '@playwright/test';

test('large citypacks search roads without rendering every road as an option',async({page})=>{
  await page.route(/\/api\/v1\/citypacks\/TOY-DUAL-CORRIDOR$/,async route=>{
    const response=await route.fetch();
    const city=await response.json();
    const geojson=city.geojson??city;
    for(let index=0;index<1200;index++){
      const id=`road-${String(index).padStart(4,'0')}`;
      geojson.features.push({type:'Feature',id,properties:{id,name:`Synthetic ${id}`},geometry:{type:'LineString',coordinates:[[24.9,60.1],[24.91,60.11]]}});
    }
    await route.fulfill({response,json:city});
  });

  await page.goto('/headless.html');
  await expect(page.getByRole('status')).toContainText('Ready');
  const picker=page.getByLabel('Add road segment');
  await expect(picker.locator('option')).toHaveCount(1);
  await page.getByLabel('Find road segment').fill('road-1199');
  await expect(picker.locator('option')).toHaveCount(2);
  await picker.selectOption('road-1199');
  await expect(page.getByRole('button',{name:'Remove road-1199'})).toBeVisible();
  await page.getByLabel('Find road segment').fill('road');
  await expect(picker.locator('option')).toHaveCount(51);
  await expect(page.getByRole('button',{name:'Remove road-1199'})).toBeVisible();
});
