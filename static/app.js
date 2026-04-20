document.addEventListener("DOMContentLoaded", function () {
  const themeToggle = document.querySelector("#theme-toggle");
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("mentorlink-theme", theme);
    if (themeToggle) {
      themeToggle.textContent = theme === "dark" ? "Dark Mode Off" : "Dark Mode On";
    }
  }
  if (themeToggle) {
    applyTheme(document.documentElement.getAttribute("data-theme") || "dark");
    themeToggle.addEventListener("click", function () {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      const target = document.querySelector(button.getAttribute("data-toggle-password"));
      if (!target) return;
      const isPassword = target.getAttribute("type") === "password";
      target.setAttribute("type", isPassword ? "text" : "password");
      button.textContent = isPassword ? "Hide" : "Show";
    });
  });
  const roleSelect = document.querySelector("#role-select");
  const roleSections = document.querySelectorAll("[data-role-section]");
  function syncRoleSections() {
    if (!roleSelect) return;
    roleSections.forEach(function (section) {
      const roleName = section.getAttribute("data-role-section");
      const shouldShow = roleName === roleSelect.value || (roleName === "mentor-membership" && roleSelect.value === "mentor");
      section.hidden = !shouldShow;
      section.style.display = shouldShow ? "grid" : "none";
    });
    syncMembershipFields();
  }
  window.syncMentorRegistration = syncRoleSections;
  if (roleSelect) {
    syncRoleSections();
    roleSelect.addEventListener("change", syncRoleSections);
    roleSelect.addEventListener("input", syncRoleSections);
  }

  const membershipType = document.querySelector("#membership-type");
  const membershipPrice = document.querySelector("[data-membership-price]");
  function syncMembershipFields() {
    if (!membershipType || !membershipPrice) return;
    membershipPrice.style.display = membershipType.value === "premium" ? "block" : "none";
  }
  if (membershipType) {
    syncMembershipFields();
    membershipType.addEventListener("change", syncMembershipFields);
  }
  const attachmentTrigger = document.querySelector("#attachment-trigger");
  const attachmentInput = document.querySelector("#attachment-input");
  const attachmentName = document.querySelector("#attachment-name");
  if (attachmentTrigger && attachmentInput) {
    attachmentTrigger.addEventListener("click", function () { attachmentInput.click(); });
    attachmentInput.addEventListener("change", function () {
      const file = attachmentInput.files && attachmentInput.files[0];
      attachmentName.textContent = file ? file.name : "No file selected";
    });
  }
  const chatMessages = document.querySelector("#chat-messages");
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
});
