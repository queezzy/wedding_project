/* rsvp.js — Formulaire RSVP pré-rempli depuis la session invité */

document.addEventListener('DOMContentLoaded', () => {

  // --------------------------------------------------------
  // Lire les données injectées par Jinja2
  // --------------------------------------------------------
  const initEl = document.getElementById('rsvp-init-data');
  if (!initEl) return;

  const { invitee, rsvp } = JSON.parse(initEl.textContent);

  const form         = document.getElementById('rsvp-form');
  const confirmation = document.getElementById('rsvp-confirmation');
  const existingDiv  = document.getElementById('rsvp-existing');
  const editBtn      = document.getElementById('rsvp-edit-btn');
  const cancelBtn    = document.getElementById('rsvp-cancel-btn');
  const submitBtn    = document.getElementById('rsvp-submit-btn');

  if (!form) return;

  // --------------------------------------------------------
  // Afficher / masquer le formulaire (mode édition)
  // --------------------------------------------------------
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      existingDiv.classList.add('rsvp-hidden');
      form.classList.remove('rsvp-form--hidden');
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      form.classList.add('rsvp-form--hidden');
      if (existingDiv) {
        existingDiv.classList.remove('rsvp-hidden');
        existingDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  // --------------------------------------------------------
  // Toggle champs menu/allergies selon présence (oui/non)
  // --------------------------------------------------------
  function setupAttendingToggle(radioName, fieldsId) {
    const radios = form.querySelectorAll(`[name="${radioName}"]`);
    const fields = document.getElementById(fieldsId);
    if (!fields) return;

    function update() {
      const checked = form.querySelector(`[name="${radioName}"]:checked`);
      fields.classList.toggle('attending-fields--hidden', checked?.value === 'false');
    }
    radios.forEach(r => r.addEventListener('change', update));
    update();
  }

  setupAttendingToggle('principal_attending', 'principal-attending-fields');
  if (invitee?.has_partner) {
    setupAttendingToggle('partner_attending', 'partner-attending-fields');
  }

  // --------------------------------------------------------
  // Compteur enfants +/−
  // --------------------------------------------------------
  const minusBtn    = document.getElementById('children-minus');
  const plusBtn     = document.getElementById('children-plus');
  const countDisp   = document.getElementById('children-count-display');
  const countInput  = document.getElementById('children-count-input');
  const childFields = document.getElementById('children-attending-fields');
  const maxChildren = countInput ? parseInt(countInput.dataset.max || '0') : 0;

  function refreshCounter(count) {
    if (countDisp)  countDisp.textContent = count;
    if (countInput) countInput.value = count;
    if (minusBtn)   minusBtn.disabled = count <= 0;
    if (plusBtn)    plusBtn.disabled  = count >= maxChildren;
    if (childFields) childFields.classList.toggle('attending-fields--hidden', count === 0);
  }

  if (minusBtn && plusBtn && countInput) {
    refreshCounter(parseInt(countInput.value || '0'));
    minusBtn.addEventListener('click', () => {
      const n = parseInt(countInput.value);
      if (n > 0) refreshCounter(n - 1);
    });
    plusBtn.addEventListener('click', () => {
      const n = parseInt(countInput.value);
      if (n < maxChildren) refreshCounter(n + 1);
    });
  }

  // --------------------------------------------------------
  // Collecte du payload JSON
  // --------------------------------------------------------
  function collectPayload() {
    const principalAttending =
      form.querySelector('[name="principal_attending"]:checked')?.value === 'true';

    const payload = {
      principal_attending:  principalAttending,
      principal_menu:       principalAttending
        ? (form.querySelector('[name="principal_menu"]')?.value || '') : '',
      principal_allergies:  principalAttending
        ? (form.querySelector('[name="principal_allergies"]')?.value?.trim() || '') : '',
      children_attending_count: parseInt(countInput?.value || '0'),
      children_ages:        form.querySelector('[name="children_ages"]')?.value?.trim() || '',
      email_contact:        document.getElementById('email-contact')?.value?.trim() || '',
      song_suggestion:      document.getElementById('song-suggestion')?.value?.trim() || '',
      message:              document.getElementById('rsvp-message')?.value?.trim() || '',
      need_accommodation:   document.getElementById('need-accommodation')?.checked || false,
    };

    if (invitee?.has_partner) {
      const partnerAttending =
        form.querySelector('[name="partner_attending"]:checked')?.value === 'true';
      payload.partner_attending  = partnerAttending;
      payload.partner_menu       = partnerAttending
        ? (form.querySelector('[name="partner_menu"]')?.value || '') : '';
      payload.partner_allergies  = partnerAttending
        ? (form.querySelector('[name="partner_allergies"]')?.value?.trim() || '') : '';
    }

    return payload;
  }

  // --------------------------------------------------------
  // Soumission
  // --------------------------------------------------------
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }

    const isEdit = !!rsvp;
    const url    = isEdit ? `/rsvp/edit/${rsvp.edit_token}` : '/api/rsvp';

    submitBtn.disabled    = true;
    submitBtn.textContent = 'Envoi en cours…';

    try {
      const res  = await fetch(url, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(collectPayload()),
      });
      const data = await res.json();

      if (!res.ok) {
        alert(data.error || 'Une erreur est survenue. Veuillez réessayer.');
        submitBtn.disabled    = false;
        submitBtn.textContent = isEdit ? 'Mettre à jour' : 'Envoyer ma réponse';
        return;
      }

      if (isEdit) {
        // Recharger la page pour afficher le résumé mis à jour
        window.location.reload();
      } else {
        // Première soumission : afficher la confirmation + token
        const editUrl  = `${window.location.origin}/rsvp/edit/${data.edit_token}`;
        const editLink = document.getElementById('rsvp-edit-link');
        if (editLink) { editLink.href = editUrl; editLink.textContent = editUrl; }
        try { localStorage.setItem('rsvp_token', data.edit_token); } catch (_) {}
        form.setAttribute('hidden', '');
        confirmation.removeAttribute('hidden');
        confirmation.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

    } catch (err) {
      console.error(err);
      alert('Erreur réseau. Veuillez vérifier votre connexion et réessayer.');
      submitBtn.disabled    = false;
      submitBtn.textContent = isEdit ? 'Mettre à jour' : 'Envoyer ma réponse';
    }
  });

  // --------------------------------------------------------
  // Livre d'or (si activé)
  // --------------------------------------------------------
  const gbForm = document.getElementById('guestbook-form');
  if (gbForm) {
    gbForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const author  = document.getElementById('gb-name')?.value.trim()    || '';
      const message = document.getElementById('gb-message')?.value.trim() || '';
      if (!author || !message) return;
      const btn = gbForm.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Envoi…';
      try {
        const res = await fetch('/api/guestbook', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ author_name: author, message }),
        });
        if (res.ok) {
          gbForm.innerHTML =
            '<p style="text-align:center;color:var(--sage-dark);font-weight:600;">' +
            'Merci\u00a0! Votre message est en attente de mod\u00e9ration. 💛</p>';
        } else {
          const d = await res.json();
          alert(d.error || 'Une erreur est survenue.');
          btn.disabled = false;
          btn.textContent = 'Laisser un message';
        }
      } catch (_) {
        alert('Erreur réseau.');
        btn.disabled = false;
        btn.textContent = 'Laisser un message';
      }
    });
  }

});


document.addEventListener('DOMContentLoaded', () => {
  const form         = document.getElementById('rsvp-form');
  const confirmation = document.getElementById('rsvp-confirmation');
  if (!form) return;

  const addPartnerBtn  = document.getElementById('add-partner');
  const removePartnerBtn = document.getElementById('remove-partner');
  const partnerBlock   = document.getElementById('guest-partner');
  const addChildBtn    = document.getElementById('add-child');
  const childrenCont   = document.getElementById('children-container');

  let childCount = 0;

  // --------------------------------------------------------
  // Partenaire
  // --------------------------------------------------------
  if (addPartnerBtn) {
    addPartnerBtn.addEventListener('click', () => {
      partnerBlock.removeAttribute('hidden');
      addPartnerBtn.closest('.partner-toggle-wrapper').setAttribute('hidden', '');
      setRequired(partnerBlock, true);
    });
  }

  if (removePartnerBtn) {
    removePartnerBtn.addEventListener('click', () => {
      partnerBlock.setAttribute('hidden', '');
      addPartnerBtn.closest('.partner-toggle-wrapper').removeAttribute('hidden');
      setRequired(partnerBlock, false);
      clearBlock(partnerBlock);
    });
  }

  // --------------------------------------------------------
  // Enfants dynamiques
  // --------------------------------------------------------
  if (addChildBtn) {
    addChildBtn.addEventListener('click', () => {
      childCount++;
      const block = createChildBlock(childCount);
      childrenCont.appendChild(block);
    });
  }

  function createChildBlock(index) {
    const id = `child-${index}`;
    const div = document.createElement('div');
    div.className = 'guest-block guest-block--child';
    div.id = id;
    div.innerHTML = `
      <div class="child-block-header">
        <h3 class="child-block-title">Enfant ${index}</h3>
        <button type="button" class="btn-remove" aria-label="Retirer l'enfant ${index}">&times;</button>
      </div>
      <div class="guest-fields">
        <div class="field-row">
          <div class="field-group">
            <label>Prénom <span class="required">*</span></label>
            <input type="text" name="${id}_firstname" required autocomplete="off" />
          </div>
          <div class="field-group">
            <label>Nom <span class="required">*</span></label>
            <input type="text" name="${id}_lastname" required autocomplete="off" />
          </div>
        </div>
        <div class="field-row">
          <div class="field-group field-group--full">
            <label>Présence <span class="required">*</span></label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" name="${id}_attending" value="true" checked />
                <span>Oui 🎉</span>
              </label>
              <label class="radio-label">
                <input type="radio" name="${id}_attending" value="false" />
                <span>Non</span>
              </label>
            </div>
          </div>
        </div>
        <div class="field-row attending-fields">
          <div class="field-group">
            <label>Choix du menu</label>
            <select name="${id}_menu">
              <option value="">— Sélectionner —</option>
              <option value="menu-enfant">Menu enfant (à compléter)</option>
              <option value="menu-enfant-vegetarien">Option végétarienne enfant</option>
            </select>
          </div>
          <div class="field-group">
            <label>Allergies / régime</label>
            <input type="text" name="${id}_allergies" placeholder="Ex : sans gluten…" maxlength="300" />
          </div>
        </div>
      </div>
    `;

    div.querySelector('.btn-remove').addEventListener('click', () => {
      div.remove();
    });

    // Gérer l'affichage conditionnel des champs selon présence
    setupAttendingToggle(div);

    return div;
  }

  // --------------------------------------------------------
  // Affichage conditionnel : champs menu/allergies si absent
  // --------------------------------------------------------
  function setupAttendingToggle(block) {
    const radios = block.querySelectorAll('[type="radio"][value]');
    radios.forEach(radio => {
      if (radio.name.endsWith('_attending')) {
        radio.addEventListener('change', () => {
          updateAttendingFields(block);
        });
      }
    });
    updateAttendingFields(block);
  }

  function updateAttendingFields(block) {
    const attending = block.querySelector('[name$="_attending"]:checked');
    const fields = block.querySelector('.attending-fields');
    if (!fields) return;
    const isAttending = !attending || attending.value === 'true';
    fields.classList.toggle('hidden', !isAttending);
  }

  // Init pour les blocs existants
  [document.getElementById('guest-main'), document.getElementById('guest-partner')]
    .filter(Boolean)
    .forEach(setupAttendingToggle);

  // --------------------------------------------------------
  // Collect form data → JSON payload
  // --------------------------------------------------------
  function collectGuests() {
    const guests = [];

    // Invité principal
    const mainFirstname = form.querySelector('[name="main_firstname"]').value.trim();
    const mainLastname  = form.querySelector('[name="main_lastname"]').value.trim();
    const mainAttending = form.querySelector('[name="main_attending"]:checked')?.value === 'true';
    const mainMenu      = mainAttending ? (form.querySelector('[name="main_menu"]')?.value || '') : '';
    const mainAllergies = mainAttending ? (form.querySelector('[name="main_allergies"]')?.value.trim() || '') : '';

    guests.push({
      first_name:  mainFirstname,
      last_name:   mainLastname,
      guest_type:  'adulte',
      attending:   mainAttending,
      menu_choice: mainMenu,
      allergies:   mainAllergies,
    });

    // Partenaire
    if (!partnerBlock.hasAttribute('hidden')) {
      const pFirstname = form.querySelector('[name="partner_firstname"]')?.value.trim() || '';
      const pLastname  = form.querySelector('[name="partner_lastname"]')?.value.trim()  || '';
      const pAttending = form.querySelector('[name="partner_attending"]:checked')?.value === 'true';
      const pMenu      = pAttending ? (form.querySelector('[name="partner_menu"]')?.value || '')  : '';
      const pAllergies = pAttending ? (form.querySelector('[name="partner_allergies"]')?.value.trim() || '') : '';

      if (pFirstname || pLastname) {
        guests.push({
          first_name:  pFirstname,
          last_name:   pLastname,
          guest_type:  'partenaire',
          attending:   pAttending,
          menu_choice: pMenu,
          allergies:   pAllergies,
        });
      }
    }

    // Enfants
    childrenCont.querySelectorAll('.guest-block--child').forEach(block => {
      const id         = block.id;
      const cFirstname = block.querySelector(`[name="${id}_firstname"]`)?.value.trim() || '';
      const cLastname  = block.querySelector(`[name="${id}_lastname"]`)?.value.trim()  || '';
      const cAttending = block.querySelector(`[name="${id}_attending"]:checked`)?.value === 'true';
      const cMenu      = cAttending ? (block.querySelector(`[name="${id}_menu"]`)?.value || '') : '';
      const cAllergies = cAttending ? (block.querySelector(`[name="${id}_allergies"]`)?.value.trim() || '') : '';

      if (cFirstname || cLastname) {
        guests.push({
          first_name:  cFirstname,
          last_name:   cLastname,
          guest_type:  'enfant',
          attending:   cAttending,
          menu_choice: cMenu,
          allergies:   cAllergies,
        });
      }
    });

    return guests;
  }

  // --------------------------------------------------------
  // Soumission
  // --------------------------------------------------------
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('rsvp-submit-btn');

    // Validation HTML5 native
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Envoi en cours…';

    const payload = {
      guests:            collectGuests(),
      email_contact:     form.querySelector('#email-contact')?.value.trim() || '',
      song_suggestion:   form.querySelector('#song-suggestion')?.value.trim() || '',
      message:           form.querySelector('#rsvp-message')?.value.trim() || '',
      need_accommodation: form.querySelector('#need-accommodation')?.checked || false,
    };

    try {
      const res = await fetch('/api/rsvp', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || 'Une erreur est survenue. Veuillez réessayer.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Envoyer ma réponse';
        return;
      }

      // Succès — afficher la confirmation
      const editToken = data.edit_token;
      const editUrl   = `${window.location.origin}/rsvp/edit/${editToken}`;
      const editLink  = document.getElementById('rsvp-edit-link');
      if (editLink) {
        editLink.href        = editUrl;
        editLink.textContent = editUrl;
      }

      // Stocker le token en localStorage pour permettre la modification
      try { localStorage.setItem('rsvp_token', editToken); } catch (_) {}

      form.setAttribute('hidden', '');
      confirmation.removeAttribute('hidden');
      confirmation.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (err) {
      console.error(err);
      alert('Une erreur réseau est survenue. Veuillez vérifier votre connexion et réessayer.');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Envoyer ma réponse';
    }
  });

  // --------------------------------------------------------
  // Bouton « Modifier ma réponse »
  // --------------------------------------------------------
  const modifyBtn = document.getElementById('rsvp-modify-btn');
  if (modifyBtn) {
    modifyBtn.addEventListener('click', async () => {
      const token = (() => {
        try { return localStorage.getItem('rsvp_token'); } catch (_) { return null; }
      })();
      if (token) {
        window.location.href = `/rsvp/edit/${token}`;
      } else {
        alert("Aucun lien de modification trouvé. Utilisez le lien affiché ci-dessus.");
      }
    });
  }

  // --------------------------------------------------------
  // Helpers
  // --------------------------------------------------------
  function setRequired(block, required) {
    block.querySelectorAll('input[type="text"], input[type="email"]').forEach(input => {
      if (required) {
        input.setAttribute('required', '');
      } else {
        input.removeAttribute('required');
      }
    });
  }

  function clearBlock(block) {
    block.querySelectorAll('input, textarea, select').forEach(el => {
      if (el.type === 'radio' || el.type === 'checkbox') {
        el.checked = el.defaultChecked;
      } else {
        el.value = el.defaultValue || '';
      }
    });
  }

  // --------------------------------------------------------
  // Livre d'or (si activé)
  // --------------------------------------------------------
  const gbForm = document.getElementById('guestbook-form');
  if (gbForm) {
    gbForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name    = document.getElementById('gb-name')?.value.trim()    || '';
      const message = document.getElementById('gb-message')?.value.trim() || '';
      if (!name || !message) return;

      const btn = gbForm.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Envoi…';

      try {
        const res = await fetch('/api/guestbook', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ author_name: name, message }),
        });
        if (res.ok) {
          gbForm.innerHTML = '<p style="text-align:center;color:var(--sage-dark);font-weight:600;">Merci ! Votre message est en attente de modération. 💛</p>';
        } else {
          const d = await res.json();
          alert(d.error || 'Une erreur est survenue.');
          btn.disabled = false;
          btn.textContent = 'Laisser un message';
        }
      } catch (_) {
        alert('Erreur réseau.');
        btn.disabled = false;
        btn.textContent = 'Laisser un message';
      }
    });
  }

});
