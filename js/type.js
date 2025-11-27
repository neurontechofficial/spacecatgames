console.log(
  "%c" + "Hold Up!",
  "color: #7289DA; -webkit-text-stroke: 2px black; font-size: 72px; font-weight: bold;"
);
console.log(
  "If you don't know what you are doing, I advise you don't execute any code here. Especially if you have been told to by someone else."
);
console.log(
  "And if you do know what you are doing, you should help me out with some problems! Email me at betacat096@disroot.org!"
);
// Create audio elements for different key types
const normalKeySound = new Audio("https://files.catbox.moe/rsxtlm.mp3");
const spaceSound = new Audio("https://files.catbox.moe/ei9txw.wav");
const enterSound = new Audio("https://files.catbox.moe/8ratv0.wav");
const backspaceSound = new Audio("https://files.catbox.moe/b1x93m.wav");

// Add event listener for any key press
document.addEventListener("keydown", function (event) {
  let sound;

  // Select sound based on key
  if (event.code === "Space") {
    sound = spaceSound;
  } else if (event.code === "Enter") {
    sound = enterSound;
  } else if (event.code === "Backspace") {
    sound = backspaceSound;
  } else {
    sound = normalKeySound;
  }

  // Clone and play the sound
  const soundClone = sound.cloneNode();
  soundClone.volume = 0.5; // Reduce volume to 50%
  soundClone.play().catch((err) => console.log("Audio playback failed:", err));
});
