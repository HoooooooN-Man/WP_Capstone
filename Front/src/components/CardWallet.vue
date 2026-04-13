<template>

<div class="wallet-container min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[#020617] text-white relative overflow-hidden font-sans">

<div class="absolute top-0 left-0 w-full h-full pointer-events-none -z-10">

<div class="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-[#4a2e1e]/10 rounded-full blur-[140px]"></div>

<div class="absolute -bottom-[10%] -right-[10%] w-[50%] h-[50%] bg-indigo-900/10 rounded-full blur-[140px]"></div>

</div>



<div class="flex flex-col items-center justify-center h-[70vh] animate-fade-in relative z-10">

<h2 class="text-3xl font-black italic tracking-tighter text-white uppercase">

{{ user.name }}'s Dashboard

</h2>

<div class="h-1 w-12 bg-[#d9b9a9] mt-3 opacity-50"></div>

<p class="mt-4 text-[#c9a999] tracking-widest uppercase text-xs">Protector System Active</p>

</div>



<div class="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[800px] h-32 bg-[#4a2e1e] rounded-t-[3.5rem] shadow-[0_-30px_60px_rgba(0,0,0,0.8)] z-40 border-t border-white/10">

<div class="absolute inset-0 opacity-60 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/leather.png')] rounded-t-[3.5rem]"></div>

<div class="absolute inset-4 border-2 border-dashed border-white/5 rounded-t-[2.5rem] pointer-events-none"></div>


<div class="flex justify-center items-end gap-6 px-10 h-full pb-8">

<div class="menu-card active w-32 h-44 bg-gradient-to-br from-slate-800 to-black rounded-xl border border-white/10 shadow-2xl cursor-pointer flex items-center justify-center">

<span class="text-[10px] font-black tracking-widest text-[#d9b9a9]">USER ID</span>

</div>

<div @click="$emit('toggle-portfolio')" class="menu-card w-32 h-44 bg-gradient-to-br from-slate-900 to-[#1e293b] rounded-xl border border-white/10 shadow-2xl cursor-pointer flex items-center justify-center">

<span class="text-[10px] font-black tracking-widest text-[#d9b9a9]">PORTFOLIO</span>

</div>

<div class="menu-card w-32 h-44 bg-gradient-to-br from-slate-900 to-[#1e293b] rounded-xl border border-white/10 shadow-2xl cursor-pointer flex items-center justify-center">

<span class="text-[10px] font-black tracking-widest text-[#d9b9a9]">ANALYTICS</span>

</div>

<div class="menu-card w-32 h-44 bg-gradient-to-br from-slate-900 to-[#1e293b] rounded-xl border border-white/10 shadow-2xl cursor-pointer flex items-center justify-center">

<span class="text-[10px] font-black tracking-widest text-[#d9b9a9]">SETTINGS</span>

</div>

</div>

</div>

</div>

</template>



<script setup lang="ts">

const props = defineProps({

isOpen: { type: Boolean, required: true },

user: { type: Object as () => { name: string; profile: string; assets: string }, required: true },

showPortfolio: { type: Boolean, required: true },

});



defineEmits(['toggle-wallet', 'toggle-portfolio']);

</script>



<style scoped>

/* @apply 대신 순수 CSS 전환 효과만 남김 */

.menu-card {

transform: translateY(110px); /* 평소엔 지갑 깊숙이 꽂혀 있음 */

transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);

}



.menu-card:hover {

transform: translateY(0px); /* 마우스 올리면 슥 올라옴 */

border-color: rgba(217, 185, 169, 0.4);

}



.menu-card.active {

transform: translateY(-20px); /* 활성화된 카드는 위로 툭 튀어나옴 */

border-color: rgba(217, 185, 169, 0.6);

box-shadow: 0 0 30px rgba(0,0,0,0.8), 0 0 20px rgba(217, 185, 169, 0.1);

}



@keyframes fadeIn {

from { opacity: 0; transform: translateY(10px); }

to { opacity: 1; transform: translateY(0); }

}



.animate-fade-in {

animation: fadeIn 1s ease-out forwards;

}

</style>