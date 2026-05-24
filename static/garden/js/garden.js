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

document.addEventListener('DOMContentLoaded', () => {
  setupPlantCards();
  setupWaterForms();
});
