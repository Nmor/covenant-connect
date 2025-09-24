import { registerBlockType } from '@wordpress/blocks';
import { __ } from '@wordpress/i18n';
import {
	PanelBody,
	RangeControl,
	SelectControl,
	ToggleControl,
} from '@wordpress/components';
import { InspectorControls, useBlockProps } from '@wordpress/block-editor';
import ServerSideRender from '@wordpress/server-side-render';

const layoutOptions = [
	{ label: __( 'List', 'covenant-connect' ), value: 'list' },
	{ label: __( 'Cards', 'covenant-connect' ), value: 'cards' },
];

const sharedDefaults = {
	limit: 5,
	layout: 'list',
	cache_minutes: 5,
};

const sermonsDefaults = {
	...sharedDefaults,
	show_preacher: true,
	show_date: true,
};

const eventsDefaults = {
	...sharedDefaults,
	show_location: true,
	show_time: true,
};

function NumberControl( {
	attribute,
	attributes,
	defaults,
	label,
	max,
	min,
	onChange,
	help,
} ) {
	return (
		<RangeControl
			label={ label }
			min={ min }
			max={ max }
			value={ attributes[ attribute ] ?? defaults[ attribute ] }
			onChange={ ( value ) =>
				onChange( attribute, value ?? defaults[ attribute ] )
			}
			help={ help }
			withInputField
		/>
	);
}

function LayoutControl( { attributes, defaults, onChange } ) {
	return (
		<SelectControl
			label={ __( 'Layout', 'covenant-connect' ) }
			value={ attributes.layout ?? defaults.layout }
			options={ layoutOptions }
			onChange={ ( value ) =>
				onChange( 'layout', value ?? defaults.layout )
			}
		/>
	);
}

function ToggleSetting( {
	attribute,
	attributes,
	defaults,
	label,
	onChange,
	help,
} ) {
	return (
		<ToggleControl
			label={ label }
			checked={ attributes[ attribute ] ?? defaults[ attribute ] }
			onChange={ ( value ) => onChange( attribute, value ) }
			help={ help }
		/>
	);
}

function createEditComponent( blockName, defaults, controls ) {
	return function Edit( { attributes, setAttributes } ) {
		const blockProps = useBlockProps();

		const updateAttribute = ( key, value ) => {
			setAttributes( { [ key ]: value } );
		};

		return (
			<div { ...blockProps }>
				<InspectorControls>
					<PanelBody
						title={ __( 'Display', 'covenant-connect' ) }
						initialOpen
					>
						<NumberControl
							attribute="limit"
							attributes={ attributes }
							defaults={ defaults }
							label={ __(
								'Number of items',
								'covenant-connect'
							) }
							min={ 1 }
							max={ 25 }
							onChange={ updateAttribute }
						/>
						<LayoutControl
							attributes={ attributes }
							defaults={ defaults }
							onChange={ updateAttribute }
						/>
						{ controls( attributes, defaults, updateAttribute ) }
					</PanelBody>
					<PanelBody
						title={ __( 'Caching', 'covenant-connect' ) }
						initialOpen={ false }
					>
						<NumberControl
							attribute="cache_minutes"
							attributes={ attributes }
							defaults={ defaults }
							label={ __(
								'Cache duration (minutes)',
								'covenant-connect'
							) }
							min={ 1 }
							max={ 60 }
							onChange={ updateAttribute }
							help={ __(
								'Caches API responses locally to reduce load.',
								'covenant-connect'
							) }
						/>
					</PanelBody>
				</InspectorControls>
				<ServerSideRender
					block={ blockName }
					attributes={ attributes }
				/>
			</div>
		);
	};
}

registerBlockType( 'covenant-connect/sermons', {
	apiVersion: 2,
	title: __( 'Covenant Connect Sermons', 'covenant-connect' ),
	description: __(
		'Display the most recent sermons from Covenant Connect.',
		'covenant-connect'
	),
	icon: 'microphone',
	category: 'widgets',
	attributes: {
		limit: { type: 'number', default: sermonsDefaults.limit },
		layout: { type: 'string', default: sermonsDefaults.layout },
		cache_minutes: {
			type: 'number',
			default: sermonsDefaults.cache_minutes,
		},
		show_preacher: {
			type: 'boolean',
			default: sermonsDefaults.show_preacher,
		},
		show_date: { type: 'boolean', default: sermonsDefaults.show_date },
	},
	edit: createEditComponent(
		'covenant-connect/sermons',
		sermonsDefaults,
		( attributes, defaults, onChange ) => (
			<>
				<ToggleSetting
					attribute="show_preacher"
					attributes={ attributes }
					defaults={ defaults }
					label={ __( 'Show preacher', 'covenant-connect' ) }
					onChange={ onChange }
				/>
				<ToggleSetting
					attribute="show_date"
					attributes={ attributes }
					defaults={ defaults }
					label={ __( 'Show date', 'covenant-connect' ) }
					onChange={ onChange }
				/>
			</>
		)
	),
	save() {
		return null;
	},
} );

registerBlockType( 'covenant-connect/events', {
	apiVersion: 2,
	title: __( 'Covenant Connect Events', 'covenant-connect' ),
	description: __(
		'Embed upcoming Covenant Connect events.',
		'covenant-connect'
	),
	icon: 'calendar-alt',
	category: 'widgets',
	attributes: {
		limit: { type: 'number', default: eventsDefaults.limit },
		layout: { type: 'string', default: eventsDefaults.layout },
		cache_minutes: {
			type: 'number',
			default: eventsDefaults.cache_minutes,
		},
		show_location: {
			type: 'boolean',
			default: eventsDefaults.show_location,
		},
		show_time: { type: 'boolean', default: eventsDefaults.show_time },
	},
	edit: createEditComponent(
		'covenant-connect/events',
		eventsDefaults,
		( attributes, defaults, onChange ) => (
			<>
				<ToggleSetting
					attribute="show_location"
					attributes={ attributes }
					defaults={ defaults }
					label={ __( 'Show location', 'covenant-connect' ) }
					onChange={ onChange }
				/>
				<ToggleSetting
					attribute="show_time"
					attributes={ attributes }
					defaults={ defaults }
					label={ __( 'Show time', 'covenant-connect' ) }
					onChange={ onChange }
					help={ __(
						'Displays start and end times when available.',
						'covenant-connect'
					) }
				/>
			</>
		)
	),
	save() {
		return null;
	},
} );
