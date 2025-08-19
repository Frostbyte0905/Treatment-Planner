(function(){
  const container = document.getElementById('rows');
  const addBtn = document.getElementById('add-row');
  const form = document.getElementById('planner-form');
  const toggleAllBtn = document.getElementById('toggle-all-monthly');
  const toggleTermsBtn = document.getElementById('toggle-finance-terms');
  const termsPanel = document.getElementById('finance-terms');

  window.addEventListener('pageshow', function(e){
    if (e.persisted && form && !form.dataset.prefill) {
      form.reset();
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    if (form && !form.dataset.prefill) form.reset();
  });

  function wireRow(row){
    const select = row.querySelector('select[name="procedure_name[]"]');
    const customField = row.querySelector('.custom-field');
    const removeBtn = row.querySelector('[data-remove]');

    function toggleCustom(){
      if(select && select.value === 'Custom'){
        customField.style.display = '';
        const input = customField.querySelector('input[name="custom_name[]"]');
        if(input) input.required = true;
      }else{
        customField.style.display = 'none';
        const input = customField.querySelector('input[name="custom_name[]"]');
        if(input) input.required = false;
      }
    }
    if(select){
      select.addEventListener('change', toggleCustom);
      toggleCustom();
    }
    if(removeBtn){
      removeBtn.addEventListener('click', () => {
        const rows = container.querySelectorAll('[data-row]');
        if(rows.length > 1){
          row.remove();
        }
      });
    }
  }

  if(container){
    container.querySelectorAll('[data-row]').forEach(wireRow);
  }

  function cloneRow(){
    const rows = container.querySelectorAll('[data-row]');
    const template = rows[rows.length - 1];
    const node = template.cloneNode(true);
    node.querySelectorAll('input').forEach(i => {
      if(i.type === 'checkbox'){ i.checked = false; }
      else { i.value = ''; }
    });
    node.querySelectorAll('textarea').forEach(t => { t.value = ''; });
    node.querySelectorAll('select').forEach(s => { s.selectedIndex = 0; });
    container.appendChild(node);
    wireRow(node);
  }

  if(addBtn){
    addBtn.addEventListener('click', cloneRow);
  }

  if(toggleAllBtn){
    toggleAllBtn.addEventListener('click', () => {
      const cbs = container.querySelectorAll('.no-finance');
      const allChecked = Array.from(cbs).every(cb => cb.checked);
      const newState = !allChecked;
      cbs.forEach(cb => cb.checked = newState);
      toggleAllBtn.textContent = newState ? 'Enable all monthly estimates' : 'Disable all monthly estimates';
    });

    const cbs = container ? container.querySelectorAll('.no-finance') : [];
    const allChecked = Array.from(cbs).length > 0 && Array.from(cbs).every(cb => cb.checked);
    toggleAllBtn.textContent = allChecked ? 'Enable all monthly estimates' : 'Disable all monthly estimates';
  }

  if(toggleTermsBtn && termsPanel){
    toggleTermsBtn.addEventListener('click', () => {
      const show = termsPanel.style.display === 'none' || termsPanel.style.display === '';
      termsPanel.style.display = show ? 'block' : 'none';
      toggleTermsBtn.textContent = show ? 'Hide financing terms' : 'Financing terms';
    });
  }

  if(form){
    form.addEventListener('submit', () => {
      form.querySelectorAll('input[name="exclude_idx[]"]').forEach(n => n.remove());
      const rows = Array.from(container.querySelectorAll('[data-row]'));
      rows.forEach((row, idx) => {
        const cb = row.querySelector('.no-finance');
        if(cb && cb.checked){
          const hidden = document.createElement('input');
          hidden.type = 'hidden';
          hidden.name = 'exclude_idx[]';
          hidden.value = String(idx);
          form.appendChild(hidden);
        }
      });
    });
  }
})();
