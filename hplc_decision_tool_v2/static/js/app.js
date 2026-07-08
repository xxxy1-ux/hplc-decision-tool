const leverActions = {
  L1: ["Try retention first: adjust organic solvent % in mobile phase", "Retention is the safest first adjustment: it changes elution times without altering selectivity or efficiency."],
  L2: ["Try selectivity: adjust pH, change organic modifier, or switch column chemistry", "Selectivity changes usually have the largest impact on resolution per unit change."],
  L3: ["Try efficiency: reduce particle size, increase column length, or check extra-column dead volume", "Efficiency gains are incremental but can push marginal Rs above specification."],
  L4: ["Try gradient elution: optimise gradient slope or add isocratic holds", "Gradient changes are more complex and are best used after simpler levers are exhausted."],
  L5: ["Escalate to method redevelopment", "All standard optimisation levers have been exhausted."],
  L6: ["Restart with isocratic optimisation", "Gradient was attempted before simpler levers, so restart systematic optimisation from retention/selectivity."]
};

function determineLeverState() {
  const retention = document.querySelector('#retention_tried')?.checked || false;
  const selectivity = document.querySelector('#selectivity_tried')?.checked || false;
  const efficiency = document.querySelector('#efficiency_tried')?.checked || false;
  const gradient = document.querySelector('#gradient_tried')?.checked || false;
  if (gradient && !retention && !selectivity && !efficiency) return 'L6';
  if (retention && selectivity && efficiency && gradient) return 'L5';
  if (retention && selectivity && efficiency) return 'L4';
  if (retention && selectivity) return 'L3';
  if (retention) return 'L2';
  return 'L1';
}

function refreshLeverCard() {
  const badge = document.querySelector('#leverStateBadge');
  if (!badge) return;
  const state = determineLeverState();
  badge.textContent = state;
  document.querySelector('#leverAction').textContent = leverActions[state][0];
  document.querySelector('#leverRationale').textContent = leverActions[state][1];
}

document.querySelectorAll('.lever-checkbox').forEach((box) => box.addEventListener('change', refreshLeverCard));

document.querySelectorAll('.copy-btn').forEach((button) => {
  button.addEventListener('click', async () => {
    const target = document.querySelector(button.dataset.copyTarget);
    if (!target) return;
    await navigator.clipboard.writeText(target.textContent);
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = 'Copy to Clipboard'; }, 1200);
  });
});
