// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://GoogleCloudPlatform.github.io',
	base: '/vertex-ai-creative-studio/',
	integrations: [
		starlight({
			title: 'GenMedia Creative Studio',
			favicon: '/favicon.ico',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio' }],
			sidebar: [
				{
					label: 'Core Application',
					items: [
						{ label: 'Introduction', slug: 'core' },
						{ label: 'Using the Studio', slug: 'core/usage' },
						{ label: 'Architecture', slug: 'core/architecture' },
						{
							label: 'Installation',
							items: [
								{ label: 'Local Setup', slug: 'core/installation/local_setup' },
								{ label: 'Deployment Guide', slug: 'core/installation/deploy' },
								{ label: 'Terraform', slug: 'core/installation/terraform' },
								{ label: 'Environment Variables', slug: 'core/installation/environment_variables' },
							]
						},
						{ label: 'Developers Guide', slug: 'core/developers_guide' },
						{ label: 'FAQ', slug: 'core/faq' },
					],
				},
				{
					label: 'AI Workflows & Demos',
					items: [
						{
							label: 'Video Generation',
							items: [
								{ label: 'Veo Variations', slug: 'experiments/veo-variations' },
								{ label: 'Run Veo Run', slug: 'experiments/run-veo-run' },
								{ label: 'Countdown Workflow', slug: 'experiments/countdown-workflow' },
								{ label: 'Creative GenMedia Workflow', slug: 'experiments/creative-genmedia-workflow' },
								{ label: 'Veo Genetic Prompt Optimizer', slug: 'experiments/veo-genetic-prompt-optimizer' },
								{ label: 'Veo 3 Character Consistency', slug: 'experiments/veo3-character-consistency' },
								{ label: 'Veo 3 Item Consistency', slug: 'experiments/veo3-item-consistency' },
							]
						},
						{
							label: 'Image Generation',
							items: [
								{ label: 'Product Recontextualization', slug: 'experiments/imagen_product_recontext' },
								{ label: 'Arena & Leaderboard', slug: 'experiments/arena' },
								{ label: 'Virtual Try-On', slug: 'experiments/vto' },
								{ label: 'Brand Consistency', slug: 'experiments/brand_consistency' }
							]
						},
						{
							label: 'Audio & Voice',
							items: [
								{ label: 'Babel', slug: 'experiments/babel' },
							]
						}
					]
				},
				{
					label: 'Developer Tools',
					items: [
						{ label: 'Promptlandia', slug: 'experiments/promptlandia' },
						{
							label: 'MCP GenMedia',
							items: [
								{ label: 'Overview', slug: 'experiments/mcp-genmedia' },
								{
									label: 'Servers',
									items: [
										{ label: 'mcp-veo-go', slug: 'experiments/mcp-genmedia/mcp-veo-go' },
										{ label: 'mcp-imagen-go', slug: 'experiments/mcp-genmedia/mcp-imagen-go' },
										{ label: 'mcp-lyria-go', slug: 'experiments/mcp-genmedia/mcp-lyria-go' },
										{ label: 'mcp-chirp3-go', slug: 'experiments/mcp-genmedia/mcp-chirp3-go' },
										{ label: 'mcp-nanobanana-go', slug: 'experiments/mcp-genmedia/mcp-nanobanana-go' },
										{ label: 'mcp-gemini-go', slug: 'experiments/mcp-genmedia/mcp-gemini-go' },
										{ label: 'mcp-avtool-go', slug: 'experiments/mcp-genmedia/mcp-avtool-go' },
									]
								},
								{
									label: 'Skills',
									autogenerate: { directory: 'experiments/mcp-genmedia/skills' }
								},
								{
									label: 'Sample Agents',
									autogenerate: { directory: 'experiments/mcp-genmedia/agents' }
								}
							]
						}
					]
				},
			],
		}),
	],
});
