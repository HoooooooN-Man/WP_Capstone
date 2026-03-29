<template>
  <div class="id-card" @transitionend="$emit('animation-finished')">
    <div class="card-header">
      <span>WALLET PROTECTOR PASSPORT</span>
      <span>🛡️</span>
    </div>
    <div class="card-body">
      <div class="user-photo">👤</div>
      <div class="user-info">
        <div class="info-group">
          <label>NICKNAME</label>
          <div class="value nickname">{{ userInfo.nickname }}</div>
        </div>
        <div class="info-group">
          <label>EMAIL</label>
          <div class="value">{{ userInfo.email }}</div>
        </div>
      </div>
    </div>
    <div class="card-footer">VERIFIED MEMBER v1.0</div>
  </div>
</template>

<script setup>
defineProps({ userInfo: Object });
defineEmits(['animation-finished']);
</script>

<style scoped>
.id-card {
  width: 380px; height: 230px; background: white; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2); display: flex; flex-direction: column;
  overflow: hidden; border: 1px solid #ccc; font-family: sans-serif;
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); /* 중앙 정렬 */
  z-index: 10; /* 지갑 위에 띄움 */
}
.card-header { background: #34495e; color: white; padding: 8px; display: flex; justify-content: space-between; }
.card-body { flex: 1; display: flex; padding: 15px; gap: 15px; align-items: center; }
.user-photo { width: 90px; height: 110px; background: #eee; display: flex; justify-content: center; align-items: center; font-size: 3.5rem; border: 1px solid #ccc; }
.user-info { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.info-group label { font-size: 0.6rem; color: #888; }
.value { font-weight: bold; border-bottom: 1px solid #eee; font-size: 0.9rem; }
.nickname { font-size: 1.1rem; color: #e67e22; }
.card-footer { font-size: 0.6rem; text-align: center; padding: 4px; color: #999; background: #f9f9f9; }
</style>