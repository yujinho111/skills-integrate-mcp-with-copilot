document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const adminPanel = document.getElementById("admin-panel");
  const adminMessage = document.getElementById("admin-message");
  const adminActivitiesList = document.getElementById("admin-activities-list");
  const activityForm = document.getElementById("activity-form");
  const loginUrl = "/admin/login";
  let currentAdmin = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function showMessage(element, message, type) {
    element.textContent = message;
    element.className = type;
    element.classList.remove("hidden");
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "An error occurred");
    }
    return result;
  }

  async function fetchActivities() {
    try {
      const activities = await requestJson("/activities");
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft = details.max_participants - details.participant_count;
        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  function renderRecentRegistrations(registrations) {
    const list = document.getElementById("recent-registrations");
    list.innerHTML = registrations.length
      ? registrations
          .map(
            (registration) =>
              `<li>${escapeHtml(registration.email)} · ${escapeHtml(registration.activity)} · ${new Date(registration.registered_at).toLocaleString()}</li>`
          )
          .join("")
      : "<li>No recent registrations</li>";
  }

  function renderActivityLog(entries) {
    const list = document.getElementById("activity-log");
    list.innerHTML = entries.length
      ? entries
          .map(
            (entry) =>
              `<li><time>${new Date(entry.timestamp).toLocaleString()}</time> · <strong>${escapeHtml(entry.actor)}</strong> · ${escapeHtml(entry.action)}: ${escapeHtml(entry.details)}</li>`
          )
          .join("")
      : "<li>No administrative actions recorded</li>";
  }

  function renderAdminActivities(activities) {
    adminActivitiesList.innerHTML = "";
    Object.entries(activities).forEach(([name, activity]) => {
      const activityCard = document.createElement("article");
      activityCard.className = "activity-card admin-activity-card";
      const participants = activity.participants.length
        ? `<ul class="participants-list">${activity.participants
            .map(
              (email) =>
                `<li><span class="participant-email">${escapeHtml(email)}</span><button class="secondary-button" data-action="unregister" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" type="button">Remove</button></li>`
            )
            .join("")}</ul>`
        : "<p><em>No participants yet</em></p>";
      const archiveButton =
        currentAdmin.role === "admin" && !activity.archived
          ? `<button class="secondary-button" data-action="archive" data-activity="${escapeHtml(name)}" type="button">Archive</button>`
          : "";

      activityCard.innerHTML = `
        <div class="admin-activity-heading">
          <div>
            <h5>${escapeHtml(name)}${activity.archived ? " (archived)" : ""}</h5>
            <p>${escapeHtml(activity.description)} · ${escapeHtml(activity.schedule)}</p>
          </div>
          <div class="admin-actions">
            <button class="secondary-button" data-action="edit" data-activity="${escapeHtml(name)}" type="button">Edit</button>
            ${archiveButton}
          </div>
        </div>
        <p>${activity.participants.length} / ${activity.max_participants} participants</p>
        <div class="participants-container">${participants}</div>
      `;
      adminActivitiesList.appendChild(activityCard);
    });
  }

  async function loadAdminData() {
    const [dashboard, activities] = await Promise.all([
      requestJson("/admin/dashboard"),
      requestJson("/admin/activities"),
    ]);
    document.getElementById("activity-count").textContent = dashboard.activity_count;
    document.getElementById("registration-count").textContent = dashboard.registration_count;
    document.getElementById("capacity-used").textContent = dashboard.capacity_used;
    document.getElementById("capacity-total").textContent = dashboard.capacity_total;
    renderRecentRegistrations(dashboard.recent_registrations);
    renderAdminActivities(activities);

    const logContainer = document.getElementById("audit-log-container");
    if (currentAdmin.role === "admin") {
      logContainer.classList.remove("hidden");
      renderActivityLog(await requestJson("/admin/activity-log"));
    } else {
      logContainer.classList.add("hidden");
    }
  }

  async function activateAdmin(user) {
    currentAdmin = user;
    document.getElementById("admin-user").textContent = `${user.username} (${user.role})`;
    loginForm.classList.add("hidden");
    adminPanel.classList.remove("hidden");
    await loadAdminData();
  }

  function resetActivityForm() {
    activityForm.reset();
    document.getElementById("editing-activity").value = "";
    document.getElementById("activity-form-title").textContent = "Create activity";
    document.getElementById("activity-submit").textContent = "Create activity";
    document.getElementById("cancel-edit").classList.add("hidden");
  }

  async function handleAdminActivityAction(button) {
    const activityName = button.dataset.activity;
    const action = button.dataset.action;
    if (action === "edit") {
      const activities = await requestJson("/admin/activities");
      const activity = activities[activityName];
      document.getElementById("editing-activity").value = activityName;
      document.getElementById("admin-activity-name").value = activityName;
      document.getElementById("admin-activity-description").value = activity.description;
      document.getElementById("admin-activity-schedule").value = activity.schedule;
      document.getElementById("admin-activity-capacity").value = activity.max_participants;
      document.getElementById("activity-form-title").textContent = "Edit activity";
      document.getElementById("activity-submit").textContent = "Save changes";
      document.getElementById("cancel-edit").classList.remove("hidden");
      activityForm.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    if (action === "archive") {
      await requestJson(`/admin/activities/${encodeURIComponent(activityName)}/archive`, {
        method: "POST",
      });
    } else if (action === "unregister") {
      await requestJson(
        `/activities/${encodeURIComponent(activityName)}/unregister?email=${encodeURIComponent(button.dataset.email)}`,
        { method: "DELETE" },
      );
    }
    await Promise.all([fetchActivities(), loadAdminData()]);
  }

  adminActivitiesList.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    try {
      await handleAdminActivityAction(button);
    } catch (error) {
      showMessage(adminMessage, error.message, "error");
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
      const user = await requestJson(loginUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      await activateAdmin(user);
      showMessage(adminMessage, "Signed in", "success");
    } catch (error) {
      showMessage(adminMessage, error.message, "error");
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await requestJson("/admin/logout", { method: "POST" });
      currentAdmin = null;
      adminPanel.classList.add("hidden");
      loginForm.classList.remove("hidden");
      loginForm.reset();
      resetActivityForm();
      showMessage(adminMessage, "Signed out", "success");
      await fetchActivities();
    } catch (error) {
      showMessage(adminMessage, error.message, "error");
    }
  });

  activityForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const editingName = document.getElementById("editing-activity").value;
    const payload = {
      name: document.getElementById("admin-activity-name").value.trim(),
      description: document.getElementById("admin-activity-description").value.trim(),
      schedule: document.getElementById("admin-activity-schedule").value.trim(),
      max_participants: Number(document.getElementById("admin-activity-capacity").value),
    };
    try {
      const url = editingName
        ? `/admin/activities/${encodeURIComponent(editingName)}`
        : "/admin/activities";
      await requestJson(url, {
        method: editingName ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      resetActivityForm();
      showMessage(adminMessage, editingName ? "Activity updated" : "Activity created", "success");
      await Promise.all([fetchActivities(), loadAdminData()]);
    } catch (error) {
      showMessage(adminMessage, error.message, "error");
    }
  });

  document.getElementById("cancel-edit").addEventListener("click", resetActivityForm);

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    try {
      const result = await requestJson(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" },
      );
      showMessage(messageDiv, result.message, "success");
      signupForm.reset();
      await fetchActivities();
      if (currentAdmin) await loadAdminData();
    } catch (error) {
      showMessage(messageDiv, error.message, "error");
    }
  });

  async function restoreAdminSession() {
    try {
      const user = await requestJson("/admin/session");
      await activateAdmin(user);
    } catch {
      currentAdmin = null;
    }
  }

  fetchActivities();
  restoreAdminSession();
});
