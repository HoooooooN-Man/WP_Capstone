<template>
  <div class="w-full h-full bg-gradient-to-br from-[#1f3756] to-[#14253a] rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.6)] p-12 lg:p-16 flex flex-col relative overflow-hidden animate-drop-in border border-white/10 text-white">
    <div class="flex justify-between items-center border-b-4 border-white/20 pb-8 z-10">
      <h2 class="text-5xl lg:text-7xl font-black tracking-tighter uppercase drop-shadow-lg">Company List</h2>
    </div>
    <div class="flex-1 flex items-center justify-center z-10">
      <p class="text-2xl lg:text-4xl font-bold opacity-50 tracking-widest">COMPANY DATA STANDBY...</p>
    </div>
  </div>
</template>

<style scoped>
@keyframes dropIn { 0% { opacity: 0; transform: translateY(-50px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
.animate-drop-in { animation: dropIn 0.8s cubic-bezier(0.165, 0.84, 0.44, 1) forwards; }
</style>