{% extends "base.html" %}
{% block title %}Users · Admin · {{ config.SITE_NAME }}{% endblock %}
{% block content %}

<div class="page-header flex items-center justify-between">
  <div>
    <div class="page-title"><i class="fa fa-users" style="color:var(--purple2)"></i> Users</div>
    <div class="page-sub">{{ pagination.total }} total</div>
  </div>
</div>

<form method="GET" class="flex gap-2 mb-2">
  <div class="search-input-wrap" style="flex:1">
    <i class="fa fa-search search-input-icon"></i>
    <input type="text" name="q" class="search-input" value="{{ q }}" placeholder="Search by name or email...">
  </div>
  <button type="submit" class="btn btn-ghost btn-sm">Search</button>
  {% if q %}<a href="{{ url_for('admin.users') }}" class="btn btn-ghost btn-sm">Clear</a>{% endif %}
</form>

<div class="table-wrap">
  <table>
    <thead>
      <tr><th>User</th><th>ID</th><th>Tier</th><th>Searches</th><th>Joined</th><th>Status</th><th>Actions</th></tr>
    </thead>
    <tbody>
      {% for u in pagination.items %}
      <tr>
        <td>
          <div class="flex items-center gap-2">
            <img src="{{ u.avatar_url }}" style="width:28px;height:28px;border-radius:50%">
            <div>
              <div style="font-size:.85rem;color:var(--text)">{{ u.full_name }}</div>
              <div style="font-size:.72rem;color:var(--text3)">{{ u.email }}</div>
            </div>
          </div>
        </td>
        <td style="font-family:monospace;font-size:.78rem;color:var(--text3)">{{ u.user_id }}</td>
        <td>
          <form method="POST" action="{{ url_for('admin.set_tier', user_id=u.id) }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <select name="tier" class="form-control quick-tier-select" style="width:110px;padding:.25rem .5rem;font-size:.78rem">
              {% for t in ['free','premium','pro','enterprise'] %}
              <option value="{{ t }}" {% if u.tier == t %}selected{% endif %}>{{ t|capitalize }}</option>
              {% endfor %}
            </select>
          </form>
        </td>
        <td style="color:var(--cyan2)">{{ u.total_searches }}</td>
        <td style="font-size:.78rem;color:var(--text3)">{{ u.created_at.strftime('%Y-%m-%d') }}</td>
        <td>
          <span class="badge badge-{{ 'approved' if u.is_active else 'rejected' }}">
            {{ 'Active' if u.is_active else 'Suspended' }}
          </span>
          {% if u.is_admin %}<span class="badge badge-pro" style="margin-left:.25rem">Admin</span>{% endif %}
        </td>
        <td>
          {% if not u.is_admin %}
          <form method="POST" action="{{ url_for('admin.toggle_user', user_id=u.id) }}" style="display:inline">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button type="submit" class="btn btn-sm {{ 'btn-danger' if u.is_active else 'btn-success' }}">
              {{ 'Suspend' if u.is_active else 'Activate' }}
            </button>
          </form>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="pagination">
  {% if pagination.has_prev %}
    <a href="?page={{ pagination.prev_num }}&q={{ q }}" class="page-btn">‹</a>
  {% endif %}
  {% for p in pagination.iter_pages() %}
    {% if p %}
      <a href="?page={{ p }}&q={{ q }}" class="page-btn {% if p == pagination.page %}active{% endif %}">{{ p }}</a>
    {% else %}
      <span class="page-btn">…</span>
    {% endif %}
  {% endfor %}
  {% if pagination.has_next %}
    <a href="?page={{ pagination.next_num }}&q={{ q }}" class="page-btn">›</a>
  {% endif %}
</div>

{% endblock %}
