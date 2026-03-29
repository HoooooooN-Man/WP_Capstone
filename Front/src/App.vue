<template>
  <div id="app" class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden">
    <AuthWallet v-if="!isLoggedIn" @login="onLogin" />
    <WalletContainer v-else
      :is-open="isWalletOpen"
      :user="user"
      :show-portfolio="showPortfolio"
      @toggle-wallet="toggleWallet"
      @toggle-portfolio="togglePortfolio"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import AuthWallet from './components/AuthWallet.vue';
import WalletContainer from './components/WalletContainer.vue';

const isLoggedIn = ref(false);
const isWalletOpen = ref(false);
const showPortfolio = ref(false);
const user = ref({ name: '', profile: '', assets: '' });

const onLogin = (payload: { name: string; style: string; totalAsset: string }) => {
  user.value = { name: payload.name, profile: payload.style, assets: payload.totalAsset };
  isLoggedIn.value = true;

  setTimeout(() => {
    isWalletOpen.value = true;
  }, 180);
};

const toggleWallet = () => {
  isWalletOpen.value = !isWalletOpen.value;
  if (!isWalletOpen.value) {
    showPortfolio.value = false;
  }
};

const togglePortfolio = () => {
  showPortfolio.value = !showPortfolio.value;
  if (showPortfolio.value && !isWalletOpen.value) {
    isWalletOpen.value = true;
  }
};
</script>

<style scoped>
/* App.vue 자체 애니메이션은 WalletContainer가 책임 */
</style>
