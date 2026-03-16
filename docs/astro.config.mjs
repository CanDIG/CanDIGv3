// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightOpenAPI, { openAPISidebarGroups } from 'starlight-openapi'
import starlightUtils from "@lorenzo_lewis/starlight-utils";

import icon from 'astro-icon';

import d2 from 'astro-d2';

// https://astro.build/config
export default defineConfig({
    site: 'https://candig.github.io',
    base: 'CanDIGv3',
    integrations: [
        d2({output: "d2"}),
        icon({
            include: {
            mdi: ["*"]
        }
    }), 
    starlight({
        title: 'Docs',
        customCss: [
            './src/styles/custom.css'
        ],
        favicon: '/favicon.ico',
        editLink: {
            baseUrl: 'https://github.com/CanDIG/CanDIGv3/edit/develop/'
        },
        logo: {
            src: './src/assets/my-logo.png',
            replacesTitle: true,
        },
        social: [{
            icon: 'github', label: 'GitHub', href:'https://github.com/candig/CanDIGv3',
        },],
    plugins: [
        starlightUtils({
            navLinks: {
                leading: { useSidebarLabelled: "headerLinks" },
            },
            multiSidebar: {
                switcherStyle: "hidden"
            }
        }),
        starlightOpenAPI([
            {
                base: 'technical/candig-api/operations',
                label: 'candig api operations',
                schema: 'https://raw.githubusercontent.com/CanDIG/candig-api/refs/heads/develop/schema.yml',
                collapsed: true
            },
            {
                base: 'technical/candig-api/authz',
                label: 'candig api auth operations',
                schema: 'https://raw.githubusercontent.com/CanDIG/candig-api/refs/heads/develop/authz-schema.yml',
                collapsed: true
            },
            {
                base: 'technical/candig-api/beacon',
                label: 'clinical beacon api',
                schema: 'https://raw.githubusercontent.com/CanDIG/candig-api/refs/heads/develop/beacon-schema.yml',
                collapsed: true
            },
            {
                base: 'technical/drs/drs-api',
                label: 'DRS api',
                schema: 'https://raw.githubusercontent.com/CanDIG/drs-service/refs/heads/stable/drs_server/drs_openapi.yaml',
                collapsed: true
            },
            {
                base: 'technical/htsget/beacon-api',
                label: 'htsget beacon api',
                schema: 'https://raw.githubusercontent.com/CanDIG/htsget_app/refs/heads/stable/htsget_server/beacon_openapi.yaml',
                collapsed: true
            },
            {
                base: 'technical/htsget/operations',
                label: 'htsget operations api',
                schema: 'https://raw.githubusercontent.com/CanDIG/htsget_app/refs/heads/stable/htsget_server/htsget_openapi.yaml',
                collapsed: true
            },
        {
                base: 'technical/federation-api',
                label: 'federation api',
                schema: 'https://raw.githubusercontent.com/CanDIG/federation_service/refs/heads/develop/candig_federation/federation.yaml',
                collapsed: true
            },
        ])
    ],
    sidebar: [
        {
            collapsed: true,
            label: 'headerLinks',
            items: [
                { label: 'Deploy', slug: 'deployment/local' },
                { label: 'Submit', slug: 'ingest' },
                { label: 'User Roles', slug: 'user-roles' },
                { label: 'Technical', slug: 'technical'}
            ]
        },
        {   
            collapsed: true,
            label: 'Deployment',
            items: [
                {
                    label: 'Deployment',
                    items: [
                        { label: 'Local deployment', slug: 'deployment/local' },
                        { label: 'Production deployment', slug: 'deployment/production'},
                        { label: 'Testing', slug: 'deployment/ingest-and-test'},
                        { label: 'Interact using Make', slug: 'deployment/interact-with-the-stack'},
                        { label: 'Logging', slug: 'deployment/logging'},
                        { label: 'Back up/Restore', slug: 'deployment/backup-restore-candig'},
                        { label: 'Troubleshooting', slug: 'deployment/stack-troubleshooting'}, 
                        { label: 'Update CanDIG', slug: 'deployment/update-candig'}
                    ]
                }
            ]
        },
        {
            label: 'Submission',
            items: [
                // Each item here is one entry in the navigation menu.
                { 
                    label: 'Data submission steps', 
                    items: 
                    [
                        'ingest/prepare-clinical', 
                        'ingest/register-programs', 
                        'ingest/ingest-clinical',
                        'ingest/prepare-genomic',
                        'ingest/ingest-genomic',
                        'ingest/ingest-help',
                    ]
                }
            ],
        },
        {
            label: 'User Roles',
            collapsed: true,
            items: [
                {
                    label: 'User Roles',
                    items:
                    [
                        {label: 'Roles Overview', slug: 'user-roles/roles-overview'},
                        {label: 'Assign user roles', slug: 'user-roles/assign-roles'},
                        {label: 'DAC Authorization', slug: 'user-roles/dac-authorization'},
                    ]
                }
            ]
            
        },
        {
            label: 'Technical Docs',
            collapsed: true,
            items: [ 
                {
                    label: 'Tech docs',
                    items: 
                    [
                        { label: 'Architecture', slug: 'technical/architecture' },
                        { label: 'Docker and submods', slug: 'technical/docker-and-submodules' },
                        ...openAPISidebarGroups,
                    ]
                }
                
                
            ]
        },
    ],
        }), d2()]
});