import uvicorn
from doodle_to_cad.config import settings

if __name__ == "__main__":
    uvicorn.run("doodle_to_cad.app:app", host=settings.host, port=settings.port, reload=False)
