function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function waterPlant(url) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    },
  });

  if (!response.ok) {
    return null;
  }

  return response.json();
}

function sortPlantCards() {
  const grid = document.querySelector('.plant-grid');
  if (!grid) {
    return;
  }

  const cards = Array.from(grid.querySelectorAll('[data-plant-card]'));
  const addCard = grid.querySelector('.add-plant-card');
  cards.sort((firstCard, secondCard) => {
    const firstMoisture = Number(firstCard.dataset.moisturePercent) || 0;
    const secondMoisture = Number(secondCard.dataset.moisturePercent) || 0;
    const moistureDiff = firstMoisture - secondMoisture;

    if (moistureDiff !== 0) {
      return moistureDiff;
    }

    return firstCard.textContent.trim().localeCompare(secondCard.textContent.trim(), undefined, {
      sensitivity: 'base',
    });
  });

  cards.forEach((card) => grid.insertBefore(card, addCard));
}

function setupPlantCards() {
  const cards = document.querySelectorAll('[data-plant-card]');
  const doubleTapDelay = 300;

  cards.forEach((card) => {
    let tapTimer = null;

    card.addEventListener('click', (event) => {
      event.preventDefault();

      if (tapTimer) {
        clearTimeout(tapTimer);
        tapTimer = null;

        waterPlant(card.dataset.waterUrl).then((data) => {
          if (!data?.ok) {
            return;
          }

          const water = card.querySelector('.plant-water');
          if (water) {
            water.style.height = `${data.moisture_percent}%`;
          }

          card.dataset.moisturePercent = data.moisture_percent;
          sortPlantCards();

          card.classList.add('is-watered');
          setTimeout(() => card.classList.remove('is-watered'), 450);
        });
        return;
      }

      tapTimer = setTimeout(() => {
        tapTimer = null;
        window.location.href = card.href;
      }, doubleTapDelay);
    });
  });
}

function setupWaterForms() {
  document.querySelectorAll('[data-water-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();

      waterPlant(form.action).then((data) => {
        if (!data?.ok) {
          form.submit();
          return;
        }

        document.querySelectorAll('.plant-water').forEach((water) => {
          water.style.height = `${data.moisture_percent}%`;
        });

        const value = document.querySelector('[data-moisture-value]');
        if (value) {
          value.textContent = data.moisture_percent;
        }
      }).catch(() => {
        form.submit();
      });
    });
  });
}

function setupFormsets() {
  document.querySelectorAll('[data-formset]').forEach((formset) => {
    const prefix = formset.dataset.formsetPrefix;
    const totalForms = formset.querySelector(`#id_${prefix}-TOTAL_FORMS`);
    const rows = formset.querySelector('[data-formset-rows]');
    const emptyForm = formset.querySelector('[data-formset-empty-form]');
    const addButton = formset.querySelector('[data-formset-add]');

    if (!prefix || !totalForms || !rows || !emptyForm || !addButton) {
      return;
    }

    const disableDeletedRowFields = (row) => {
      row.querySelectorAll('input, select, textarea').forEach((field) => {
        if (field.name.endsWith('-DELETE') || field.name.endsWith('-id')) {
          return;
        }
        field.disabled = true;
      });
    };

    const markRowDeleted = (row) => {
      const deleteInput = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleteInput) {
        deleteInput.checked = true;
      }
      row.classList.add('is-deleted');
      disableDeletedRowFields(row);
    };

    const getVisibleRows = () => Array.from(rows.querySelectorAll('[data-formset-row]'))
      .filter((row) => !row.classList.contains('is-deleted'));

    const updateComponentOptions = () => {
      const visibleRows = getVisibleRows();
      const selects = visibleRows
        .map((row) => row.querySelector('select'))
        .filter(Boolean);
      const selectedValues = new Set(selects.map((select) => select.value).filter(Boolean));
      const allValues = new Set();

      selects.forEach((select) => {
        Array.from(select.options).forEach((option) => {
          if (option.value) {
            allValues.add(option.value);
          }
        });
      });

      selects.forEach((select) => {
        Array.from(select.options).forEach((option) => {
          option.disabled = Boolean(
            option.value && option.value !== select.value && selectedValues.has(option.value),
          );
        });
      });

      addButton.disabled = allValues.size > 0 && selectedValues.size >= allValues.size;
    };

    addButton.addEventListener('click', () => {
      const index = Number(totalForms.value);
      const html = emptyForm.innerHTML.replaceAll('__prefix__', String(index));
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html.trim();
      rows.appendChild(wrapper.firstElementChild);
      totalForms.value = String(index + 1);
      updateComponentOptions();
    });

    rows.addEventListener('change', (event) => {
      if (event.target.matches('select')) {
        updateComponentOptions();
      }
    });

    rows.addEventListener('click', (event) => {
      const removeButton = event.target.closest('[data-formset-remove]');
      if (!removeButton) {
        return;
      }

      event.preventDefault();

      const row = removeButton.closest('[data-formset-row]');
      if (!row) {
        return;
      }

      markRowDeleted(row);
      updateComponentOptions();
    });

    rows.querySelectorAll('[data-formset-row].is-deleted').forEach(disableDeletedRowFields);
    updateComponentOptions();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupPlantCards();
  setupWaterForms();
  setupFormsets();
});
