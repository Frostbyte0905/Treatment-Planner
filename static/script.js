(function(){
  const container = document.getElementById('rows');
  const addBtn = document.getElementById('add-row');
  const form = document.getElementById('planner-form');

  // Only reset when not editing
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
    node.querySelectorAll('input').forEach(i => { i.value = ''; });
    node.querySelectorAll('textarea').forEach(t => { t.value = ''; });
    node.querySelectorAll('select').forEach(s => { s.selectedIndex = 0; });
    container.appendChild(node);
    wireRow(node);
  }

  if(addBtn){
    addBtn.addEventListener('click', cloneRow);
  }
})();
