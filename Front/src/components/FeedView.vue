<template>
  <div class="w-full h-full bg-gradient-to-br from-[#2edc68] to-[#1cb550] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] p-12 lg:p-16 flex flex-col relative overflow-hidden animate-drop-in border border-white/20 text-white">
    <div class="flex justify-between items-center border-b-4 border-white/30 pb-8 z-10">
      <h2 class="text-5xl lg:text-7xl font-black tracking-tighter uppercase drop-shadow-md">Latest Feed</h2>
    </div>
    <div class="flex-1 flex items-center justify-center z-10">
      <p class="text-2xl lg:text-4xl font-bold opacity-80 tracking-widest drop-shadow-sm">FEED SYSTEM STANDBY...</p>
    </div>
  </div>
</template>

<style scoped>
.animate-drop-in { animation: drop-in 0.7s var(--ease-wallet) forwards; }
</style>