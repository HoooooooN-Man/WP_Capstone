<template>
  <div id="app">
    <transition name="fade" mode="out-in">
      <AuthWallet v-if="!auth.isLoggedIn" key="auth" />
      <CardWallet v-else key="wallet" :user="{ name: auth.nickname ?? 'User' }" />
    </transition>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth.js'
import AuthWallet from '@/components/wallet/AuthWallet.vue'
import CardWallet from '@/components/wallet/CardWallet.vue'

const auth = useAuthStore()
</script>
