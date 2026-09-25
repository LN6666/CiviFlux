import {test,expect} from '@playwright/test';

test('attention search and pages keep a large result browsable',async({page})=>{
  await page.route(/\/api\/v1\/runs\/[^/]+\/results$/,async route=>{
    const response=await route.fetch();
    const result=await response.json();
    const sample=result.attention.records[0];
    result.attention.records=Array.from({length:205},(_,index)=>({
      ...sample,
      object_id:`object-${String(index).padStart(3,'0')}`,
      rank_within_type:index+1,
    }));
    await route.fulfill({response,json:result});
  });

  await page.goto('/headless.html');
  await expect(page.getByRole('status')).toContainText('Ready');
  await page.getByLabel('Confirm scenario assumptions',{exact:true}).check();
  await page.getByRole('button',{name:'Validate & run'}).click();
  await expect(page.getByRole('status')).toContainText('Complete',{timeout:25000});
  await page.getByRole('tab',{name:'Attention'}).click();

  const table=page.getByRole('table',{name:'Graph attention scores'});
  await expect(table.locator('tbody tr')).toHaveCount(100);
  await expect(page.getByText('Showing 1–100 of 205 objects')).toBeVisible();
  const inlineDiagnostics=await page.getByText('Convergence and run diagnostics').locator('..').locator('pre').textContent();
  expect(inlineDiagnostics?.length).toBeLessThan(5000);
  await page.getByRole('button',{name:'Next attention page'}).click();
  await expect(table.locator('tbody tr')).toHaveCount(100);
  await expect(table).toContainText('object-100');
  await expect(page.getByText('Showing 101–200 of 205 objects')).toBeVisible();

  await page.getByLabel('Find attention object').fill('object-204');
  await expect(table.locator('tbody tr')).toHaveCount(1);
  await expect(table).toContainText('object-204');
  await expect(page.getByText('Showing 1–1 of 1 objects')).toBeVisible();
  await expect(page.getByRole('button',{name:'Next attention page'})).toBeDisabled();
  expect(await page.evaluate(()=>{
    const panel=document.querySelector('urban-impact-panel') as unknown as {result?:{attention?:{records?:unknown[]}}};
    return panel?.result?.attention?.records?.length;
  })).toBe(205);
});
