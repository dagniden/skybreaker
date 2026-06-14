const timeline = document.querySelector('[data-timeline]');

if (timeline) {
  const years = [...timeline.querySelectorAll('[data-year]')];
  const dateGroups = [...timeline.querySelectorAll('[data-date-group]')];
  const dateButtons = [...timeline.querySelectorAll('[data-event-target]')];
  const events = [...timeline.querySelectorAll('[data-event]')];
  const bgImage = timeline.querySelector('[data-bg-image]');

  function activateEvent(eventId) {
    const event = events.find((item) => item.dataset.event === eventId);

    if (!event) {
      return;
    }

    const yearId = event.dataset.year;

    years.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.year === yearId);
    });

    dateGroups.forEach((group) => {
      group.classList.toggle('is-active', group.dataset.dateGroup === yearId);
    });

    dateButtons.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.eventTarget === eventId);
    });

    events.forEach((item) => {
      item.classList.toggle('is-active', item === event);
    });

    if (bgImage && event.dataset.image) {
      if (bgImage.tagName === 'IMG') {
        bgImage.src = event.dataset.image;
        bgImage.alt = event.dataset.imageAlt || event.querySelector('h1')?.textContent || '';
      } else {
        bgImage.style.backgroundImage = `url("${event.dataset.image}")`;
      }
    }
  }

  years.forEach((button) => {
    button.addEventListener('click', () => {
      const group = dateGroups.find((item) => item.dataset.dateGroup === button.dataset.year);
      const firstDate = group?.querySelector('[data-event-target]');

      if (firstDate) {
        activateEvent(firstDate.dataset.eventTarget);
      }
    });
  });

  dateButtons.forEach((button) => {
    button.addEventListener('click', () => {
      activateEvent(button.dataset.eventTarget);
    });
  });
}
