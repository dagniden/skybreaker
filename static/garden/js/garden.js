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

document.addEventListener('DOMContentLoaded', () => {
  setupPlantCards();
  setupWaterForms();
});
