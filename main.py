from assistant.listener import Listener
from assistant.brain import Brain

def main():
		print("Starting Blancassist...")
		brain = Brain(require_wake_word=True)
		listener = Listener(on_phrase=brain.handle)

		try:
				listener.start()
		except KeyboardInterrupt:
				listener.stop()
				print("Blancassist stopped.")

if __name__ == "__main__":
    main()