from shiny import App, reactive, ui, render
import shinyswatch
from chatlas import ChatOpenAI, ChatAnthropic
from google import genai
from google.genai import types
from dotenv import load_dotenv
import requests
from PIL import Image
from io import BytesIO
import base64

_ = load_dotenv()

google_genAI = genai.Client()

chat_session_openAI = ChatOpenAI(
    model="gpt-4o",
    system_prompt="No more than 300 characters per answer. Be seriously. "
    "You are a helpful assistant that can look up real jokes if asked to do so.",
)
chat_session_claude = ChatAnthropic(
    model="claude-3-5-sonnet-latest",
    system_prompt="No more than 300 characters per answer and dont take the input seriously. "
    "Pull it through the dirt. You are a helpful assistant that can look up real jokes if asked to do so.",
)

# maybe useful https://icanhazdadjoke.com/
# tool calling
def get_a_joke():
    """
    With this function you can look up a real joke when you need.
    """
    call_API = True
    if call_API:
        print("[JOKE API CALLED]")
        base_url = "https://api.humorapi.com/jokes/search"
        params = {
            "keywords": "elephant",
            "number": 1,
            "api-key": "e3a6f16463f5456eba4c13f84ba3fc81",
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.text
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
    else:
        print("[fake JOKE API CALLED]")
        return "Why don't elephants use computers? Because they're afraid of the mouse!"

#chat_session_openAI.register_tool(get_a_joke)
#chat_session_claude.register_tool(get_a_joke)

def get_generated_image(contents):
    if contents == None:
        contents = ('Hi, can you create a 3d rendered image of a jolly pink elephant '
                    'with wings and a top hat flying over a happy '
                    'futuristic scifi water world with lots of blue little lovely birds?')

    response = google_genAI.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
        response_modalities=['Text', 'Image']
        )
    )
    resized_img = None
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            resized_img = part.text
            print(f"[genAI TEXT] {resized_img}")
        elif part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            #image.save(f'gemini-native-image5.png')
            width, height = image.size
            new_height = 250
            new_width = int((new_height / height) * width)  # resize to 150px
            resized_img = image.resize((new_width, new_height), Image.LANCZOS)
            print("[INFO] There is an image!")
        else:
            resized_img = "[INFO] no image from gemini-2.0-flash-exp-image-generation"
            print("[INFO] No image, no text")
    return resized_img


def pil_image_to_b64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


app_ui = ui.page_fluid(
    # Context input with image
    ui.row(
        ui.column(8,
            ui.input_text_area("text1", "Set the context to initiate the conversation", 
                value="why are elephants not pink", 
                placeholder="why are elephants not pink", 
                width="50ch", height="5em")
        ),
        ui.column(4,
        )
    ),
    ui.input_action_button("enter1", "Context"),
    ui.tags.hr(style="border: 1px solid #ccc; margin: 10px 0;"),
    
    ui.row(
        ui.column(8,
            ui.input_text_area("text2", "answer of funny Claude", 
                value="", 
                width="100ch", height="10em")
        ),
        ui.column(4,
            ui.output_ui("image_output_openAI"),
        )
    ),
    ui.input_action_button("enter2", "send to serious ChatGPT"),
    ui.tags.hr(style="border: 1px solid #ccc; margin: 10px 0;"),
    
    ui.row(
        ui.column(8,
            ui.input_text_area("text3", "answer of serious OpenAI", 
                value="", 
                width="100ch", height="10em")
        ),
        ui.column(4,
            ui.output_ui("image_output_claude"),
        )
    ),
    ui.input_action_button("enter3", "send to funny Claude"),
    theme=shinyswatch.theme.minty,
)

def server(input, output, session):
    image_data_claude = reactive.Value()  # docs https://rstudio.github.io/cheatsheets/html/shiny-python.html
    image_data_openAI = reactive.Value()
    joke_data_fetched = reactive.Value()
    joke_data_fetched.set("test joke")

    @reactive.Effect
    @reactive.event(input.enter1)
    def _():
        response = chat_session_openAI.chat(input.text1(), echo='none')
        ui.update_text("text3", value=response.get_content())

    @reactive.Effect
    @reactive.event(input.enter2)
    def _():
        response = chat_session_openAI.chat(input.text2(), echo='none')
        ui.update_text("text3", value=response.get_content())
        print("[INFO] got openAI text")
        chat_sumarize = ChatAnthropic(
            model="claude-3-5-sonnet-latest",
            system_prompt="No more than 80 characters per answer. Make a description for an image. Stay true to the text.",
        )
        response_img_sum = chat_sumarize.chat(response.get_content(), echo='none')
        response_img_sum_augmented = response_img_sum.get_content() + "\ngenerate a colorful, happy image. I really need an image! please"
        print(f"[IMG SUM in got openAI text] {response_img_sum.get_content()}")
        image = get_generated_image(contents=response_img_sum_augmented)
        #if len(image) > 500:
        if isinstance(image, Image.Image):
            image_data_openAI.set(pil_image_to_b64(image))
        else:
            image_data_openAI.set(image)

    @reactive.Effect
    @reactive.event(input.enter3)
    def _():
        response = chat_session_claude.chat(input.text3(), echo='none')
        ui.update_text("text2", value=response.get_content())
        print("[INFO] claude text")
        chat_sumarize = ChatAnthropic(
            model="claude-3-5-sonnet-latest",
            system_prompt="No more than 80 characters per answer. Make a description for an image. Keep funny key statements. Stay in the fantasy world. The summary should be humorous. Stay true to the text.",
        )
        response_img_sum = chat_sumarize.chat(response.get_content(), echo='none')
        response_img_sum_augmented = response_img_sum.get_content() + " generate a colorful, happy image. I really need an image! please"
        print(f"[IMG SUM in got claude text] {response_img_sum_augmented}")
        image = get_generated_image(contents=response_img_sum.get_content())
        #if len(image) > 500:
        if isinstance(image, Image.Image):
            image_data_claude.set(pil_image_to_b64(image))
        else:
            image_data_claude.set(image)

    @render.ui
    def image_output_openAI():
        image_gen = image_data_claude.get()
        if image_gen is None:
            return ui.p("Image will be generated depending on conversation and the mood of gemini-2.0-flash-exp-image-generation")
        else:
            print(f"[in image_output_openAI] is Image.Image? {isinstance(image_gen, Image.Image)}")
            return ui.tags.img(
                src=f"data:image/png;base64,{image_gen}",
                style="max-width: 100%; border: 1px solid #ddd; padding: 5px;"
            )
        
    @render.ui
    def image_output_claude():
        image_gen = image_data_openAI.get()
        if image_gen is None:
            return ui.p("Image will be generated depending on conversation and the mood of gemini-2.0-flash-exp-image-generation")
        else:
            print(f"[in image_output_claude] is Image.Image? {isinstance(image_gen, Image.Image)}")
            return ui.tags.img(
                src=f"data:image/png;base64,{image_gen}",
                style="max-width: 100%; border: 1px solid #ddd; padding: 5px;"
            )

app = App(app_ui, server)
