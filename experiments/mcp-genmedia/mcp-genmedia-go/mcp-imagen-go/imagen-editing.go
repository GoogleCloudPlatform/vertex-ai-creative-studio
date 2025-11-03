// Package main implements an MCP server for Google's Imagen models.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"google.golang.org/genai"
)

// SegmentationClassMap maps human-readable names to the integer IDs required by the Imagen API.
var SegmentationClassMap = map[string]int32{
	"backpack": 0, "umbrella": 1, "bag": 2, "tie": 3, "suitcase": 4, "case": 5, "bird": 6, "cat": 7, "dog": 8, "horse": 9, "sheep": 10, "cow": 11, "elephant": 12, "bear": 13, "zebra": 14, "giraffe": 15, "animal (other)": 16, "microwave": 17, "radiator": 18, "oven": 19, "toaster": 20, "storage tank": 21, "conveyor belt": 22, "sink": 23, "refrigerator": 24, "washer dryer": 25, "fan": 26, "dishwasher": 27, "toilet": 28, "bathtub": 29, "shower": 30, "tunnel": 31, "bridge": 32, "pier wharf": 33, "tent": 34, "building": 35, "ceiling": 36, "laptop": 37, "keyboard": 38, "mouse": 39, "remote": 40, "cell phone": 41, "television": 42, "floor": 43, "stage": 44, "banana": 45, "apple": 46, "sandwich": 47, "orange": 48, "broccoli": 49, "carrot": 50, "hot dog": 51, "pizza": 52, "donut": 53, "cake": 54, "fruit (other)": 55, "food (other)": 56, "chair (other)": 57, "armchair": 58, "swivel chair": 59, "stool": 60, "seat": 61, "couch": 62, "trash can": 63, "potted plant": 64, "nightstand": 65, "bed": 66, "table": 67, "pool table": 68, "barrel": 69, "desk": 70, "ottoman": 71, "wardrobe": 72, "crib": 73, "basket": 74, "chest of drawers": 75, "bookshelf": 76, "counter (other)": 77, "bathroom counter": 78, "kitchen island": 79, "door": 80, "light (other)": 81, "lamp": 82, "sconce": 83, "chandelier": 84, "mirror": 85, "whiteboard": 86, "shelf": 87, "stairs": 88, "escalator": 89, "cabinet": 90, "fireplace": 91, "stove": 92, "arcade machine": 93, "gravel": 94, "platform": 95, "playingfield": 96, "railroad": 97, "road": 98, "snow": 99, "sidewalk pavement": 100, "runway": 101, "terrain": 102, "book": 103, "box": 104, "clock": 105, "vase": 106, "scissors": 107, "plaything (other)": 108, "teddy bear": 109, "hair dryer": 110, "toothbrush": 111, "painting": 112, "poster": 113, "bulletin board": 114, "bottle": 115, "cup": 116, "wine glass": 117, "knife": 118, "fork": 119, "spoon": 120, "bowl": 121, "tray": 122, "range hood": 123, "plate": 124, "person": 125, "rider (other)": 126, "bicyclist": 127, "motorcyclist": 128, "paper": 129, "streetlight": 130, "road barrier": 131, "mailbox": 132, "cctv camera": 133, "junction box": 134, "traffic sign": 135, "traffic light": 136, "fire hydrant": 137, "parking meter": 138, "bench": 139, "bike rack": 140, "billboard": 141, "sky": 142, "pole": 143, "fence": 144, "railing banister": 145, "guard rail": 146, "mountain hill": 147, "rock": 148, "frisbee": 149, "skis": 150, "snowboard": 151, "sports ball": 152, "kite": 153, "baseball bat": 154, "baseball glove": 155, "skateboard": 156, "surfboard": 157, "tennis racket": 158, "net": 159, "base": 160, "sculpture": 161, "column": 162, "fountain": 163, "awning": 164, "apparel": 165, "banner": 166, "flag": 167, "blanket": 168, "curtain (other)": 169, "shower curtain": 170, "pillow": 171, "towel": 172, "rug floormat": 173, "vegetation": 174, "bicycle": 175, "car": 176, "autorickshaw": 177, "motorcycle": 178, "airplane": 179, "bus": 180, "train": 181, "truck": 182, "trailer": 183, "boat ship": 184, "slow wheeled object": 185, "river lake": 186, "sea": 187, "water (other)": 188, "swimming pool": 189, "waterfall": 190, "wall": 191, "window": 192, "window blind": 193,
}

// registerImagenEditingTools adds all the editing-related tools and prompts to the MCP server.
func registerImagenEditingTools(s *server.MCPServer, client *genai.Client, appConfig *common.Config) {
	// Add the segmentation classes resource
	s.AddResource(mcp.NewResource(
		"imagen://segmentation_classes",
		"Imagen Segmentation Classes",
		mcp.WithResourceDescription("A list of supported segmentation classes for semantic masking."),
		mcp.WithMIMEType("application/json"),
	), func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		jsonData, err := json.MarshalIndent(SegmentationClassMap, "", "  ")
		if err != nil {
			return nil, fmt.Errorf("failed to marshal segmentation classes: %w", err)
		}
		return []mcp.ResourceContents{
			mcp.TextResourceContents{
				URI:      "imagen://segmentation_classes",
				MIMEType: "application/json",
				Text:     string(jsonData),
			},
		},
		nil
	})

	// Inpainting Insert Tool
	s.AddTool(mcp.NewTool("imagen_edit_inpainting_insert",
		mcp.WithDescription("Adds content to a masked area of an image."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("A description of the content to add.")),
		mcp.WithString("image_uri", mcp.Required(), mcp.Description("The GCS URI of the image to edit.")),
		mcp.WithString("mask_mode", mcp.Required(), mcp.Description("The masking mode to use (e.g., MASK_MODE_FOREGROUND, MASK_MODE_SEMANTIC).")),
		mcp.WithNumber("mask_dilation", mcp.Description("The dilation to apply to the mask.")),
		mcp.WithArray("segmentation_classes", mcp.Description("The segmentation classes to use for semantic masking.")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return imagenEditHandler(ctx, request, client, appConfig)
	})

	// Inpainting Remove Tool
	s.AddTool(mcp.NewTool("imagen_edit_inpainting_remove",
		mcp.WithDescription("Removes content from a masked area of an image."),
		mcp.WithString("image_uri", mcp.Required(), mcp.Description("The GCS URI of the image to edit.")),
		mcp.WithString("mask_mode", mcp.Required(), mcp.Description("The masking mode to use (e.g., MASK_MODE_FOREGROUND, MASK_MODE_SEMANTIC).")),
		mcp.WithNumber("mask_dilation", mcp.Description("The dilation to apply to the mask.")),
		mcp.WithArray("segmentation_classes", mcp.Description("The segmentation classes to use for semantic masking.")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return imagenEditHandler(ctx, request, client, appConfig)
	})

	// Edit Image Area Prompt
	s.AddPrompt(mcp.NewPrompt("edit_image_area",
		mcp.WithPromptDescription("Interactively guides a user to add or remove content from a specific area of an image."),
		mcp.WithArgument("image_uri", mcp.ArgumentDescription("The GCS URI of the image to edit."), mcp.RequiredArgument()),
		mcp.WithArgument("prompt", mcp.ArgumentDescription("A description of the desired change (e.g., \"add a hat\", \"remove the car\")."), mcp.RequiredArgument()),
	), func(ctx context.Context, request mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		imageURI, ok := request.Params.Arguments["image_uri"]
		if !ok || strings.TrimSpace(imageURI) == "" {
			return mcp.NewGetPromptResult(
				"Missing Image URI",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent("What image (GCS URI) would you like to edit?")),
				},
			),
			nil
		}

		prompt, ok := request.Params.Arguments["prompt"]
		if !ok || strings.TrimSpace(prompt) == "" {
			return mcp.NewGetPromptResult(
				"Missing Prompt",
				[]mcp.PromptMessage{
					mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent("What would you like to do? (e.g., \"add a hat\", \"remove the car\")")),
				},
			),
			nil
		}

		// Determine the tool to call based on the prompt
		var toolName string
		if strings.Contains(strings.ToLower(prompt), "remove") || strings.Contains(strings.ToLower(prompt), "delete") {
			toolName = "imagen_edit_inpainting_remove"
		} else {
			toolName = "imagen_edit_inpainting_insert"
		}

		// Call the appropriate tool
		args := make(map[string]interface{}, len(request.Params.Arguments))
		for k, v := range request.Params.Arguments {
			args[k] = v
		}
		toolRequest := mcp.CallToolRequest{
			Params: mcp.CallToolParams{Name: toolName, Arguments: args},
		}
		result, err := imagenEditHandler(ctx, toolRequest, client, appConfig)
		if err != nil {
			return nil, err
		}

		var responseText string
		for _, content := range result.Content {
			if textContent, ok := content.(mcp.TextContent); ok {
				responseText += textContent.Text + "\n"
			}
		}

		return mcp.NewGetPromptResult(
			"Image Editing Result",
			[]mcp.PromptMessage{
				mcp.NewPromptMessage(mcp.RoleAssistant, mcp.NewTextContent(strings.TrimSpace(responseText))),
			},
		),
		nil
	})
}

func imagenEditHandler(ctx context.Context, request mcp.CallToolRequest, client *genai.Client, appConfig *common.Config) (*mcp.CallToolResult, error) {
	args := request.GetArguments()

	// Determine the edit mode from the tool name
	var editMode genai.EditMode
	switch request.Params.Name {
	case "imagen_edit_inpainting_insert":
		editMode = genai.EditModeInpaintInsertion
	case "imagen_edit_inpainting_remove":
		editMode = genai.EditModeInpaintRemoval
	default:
		return mcp.NewToolResultError(fmt.Sprintf("unsupported tool for imagenEditHandler: %s", request.Params.Name)), nil
	}

	// Get the required arguments
	prompt, _ := args["prompt"].(string)
	imageURI, ok := args["image_uri"].(string)
	if !ok || imageURI == "" {
		return mcp.NewToolResultError("image_uri is a required argument"), nil
	}

	// Download the image data from GCS.
	imageData, err := common.DownloadFromGCSAsBytes(ctx, imageURI)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("failed to download image from GCS: %v", err)), nil
	}

	// Construct the reference images
	rawRefImg := &genai.RawReferenceImage{
		ReferenceImage: &genai.Image{ImageBytes: imageData},
		ReferenceID:    1,
	}

	maskMode, _ := args["mask_mode"].(string)
	maskDilation, _ := args["mask_dilation"].(float64)
	segmentationClasses, _ := args["segmentation_classes"].([]interface{})

	var maskRefImg *genai.MaskReferenceImage
	if maskMode != "" {
		maskRefImg = &genai.MaskReferenceImage{
			ReferenceID: 2,
			Config: &genai.MaskReferenceConfig{
				MaskMode: genai.MaskReferenceMode(maskMode),
			},
		}

		if maskDilation > 0 {
			maskRefImg.Config.MaskDilation = genai.Ptr[float32](float32(maskDilation))
		}

		if len(segmentationClasses) > 0 {
			var classes []int32
			for _, class := range segmentationClasses {
				if c, ok := class.(float64); ok {
					classes = append(classes, int32(c))
				} else if c, ok := class.(string); ok {
					if id, ok := SegmentationClassMap[c]; ok {
						classes = append(classes, id)
					} else {
						return mcp.NewToolResultError(fmt.Sprintf("unknown segmentation class: %s", c)), nil
					}
				}
			}
			maskRefImg.Config.SegmentationClasses = classes
		}
	}

	var referenceImages []genai.ReferenceImage
	referenceImages = append(referenceImages, rawRefImg)
	if maskRefImg != nil {
		referenceImages = append(referenceImages, maskRefImg)
	}

	// Construct the edit config
	editConfig := &genai.EditImageConfig{
		EditMode: editMode,
	}

	// Call the EditImage method
	referenceImagesJSON, _ := json.MarshalIndent(referenceImages, "", "  ")
	log.Printf("Calling EditImage with referenceImages:\n%s", string(referenceImagesJSON))
	editConfigJSON, _ := json.MarshalIndent(editConfig, "", "  ")
	log.Printf("Calling EditImage with editConfig:\n%s", string(editConfigJSON))

	response, err := client.Models.EditImage(
		ctx,
		"imagen-3.0-capability-001",
		prompt,
		referenceImages,
		editConfig,
	)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("error editing image: %v", err)), nil
	}

	// Process the response
	var resultText string
	if len(response.GeneratedImages) > 0 {
		genImg := response.GeneratedImages[0]
		if genImg.Image != nil && len(genImg.Image.ImageBytes) > 0 {
			// The image data is in ImageBytes, so we need to upload it to GCS.
			// First, create a unique filename for the image.
			filename := fmt.Sprintf("edited-image-%d.png", time.Now().UnixNano())
			// Now, upload the image to GCS.
			if err := common.UploadToGCS(ctx, appConfig.GenmediaBucket, filename, "image/png", genImg.Image.ImageBytes); err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("error uploading edited image to GCS: %v", err)), nil
			}
			gcsURI := fmt.Sprintf("gs://%s/%s", appConfig.GenmediaBucket, filename)
			resultText = fmt.Sprintf("Image edited successfully. Edited image URI: %s", gcsURI)
		} else if genImg.Image != nil && genImg.Image.GCSURI != "" {
			// The image is already in GCS.
			resultText = fmt.Sprintf("Image edited successfully. Edited image URI: %s", genImg.Image.GCSURI)
		} else {
			resultText = "Image editing did not produce any images."
		}
	} else {
		resultText = "Image editing did not produce any images."
	}

	return mcp.NewToolResultText(resultText), nil
}
