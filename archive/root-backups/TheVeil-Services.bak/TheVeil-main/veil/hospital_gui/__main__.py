import uvicorn
from .main import app

def main() -> None:
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )

if __name__ == "__main__":
    main()
