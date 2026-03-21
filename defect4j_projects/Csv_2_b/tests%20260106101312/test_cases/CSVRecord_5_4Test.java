package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_5_4Test {

    private CSVRecord csvRecordWithMapping;
    private CSVRecord csvRecordWithoutMapping;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() throws Exception {
        // Prepare mapping with some keys
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);

        // Create CSVRecord instance with mapping
        csvRecordWithMapping = new CSVRecord(new String[]{"value1", "value2"}, mapping, "comment", 1L);

        // Create CSVRecord instance without mapping (mapping == null)
        csvRecordWithoutMapping = new CSVRecord(new String[]{"value1", "value2"}, null, "comment", 2L);
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withMapping_keyPresent() {
        assertTrue(csvRecordWithMapping.isMapped("header1"));
        assertTrue(csvRecordWithMapping.isMapped("header2"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withMapping_keyAbsent() {
        assertFalse(csvRecordWithMapping.isMapped("absentHeader"));
        assertFalse(csvRecordWithMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withoutMapping() {
        assertFalse(csvRecordWithoutMapping.isMapped("header1"));
        assertFalse(csvRecordWithoutMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_reflection_onPrivateMappingField() throws Exception {
        // Create CSVRecord with null mapping first
        CSVRecord record = new CSVRecord(new String[]{"v1"}, null, null, 0L);

        // Use reflection to set private final field 'mapping' to a mock Map
        Field mappingField = CSVRecord.class.getDeclaredField("mapping");
        mappingField.setAccessible(true);

        @SuppressWarnings("unchecked")
        Map<String, Integer> mockMap = mock(Map.class);
        when(mockMap.containsKey("key")).thenReturn(true);
        when(mockMap.containsKey("other")).thenReturn(false);
        when(mockMap.containsKey(null)).thenReturn(false);

        // Remove final modifier from the field to allow setting it
        Field modifiersField = Field.class.getDeclaredField("modifiers");
        modifiersField.setAccessible(true);
        modifiersField.setInt(mappingField, mappingField.getModifiers() & ~java.lang.reflect.Modifier.FINAL);

        mappingField.set(record, mockMap);

        assertTrue(record.isMapped("key"));
        assertFalse(record.isMapped("other"));
        assertFalse(record.isMapped(null));

        verify(mockMap).containsKey("key");
        verify(mockMap).containsKey("other");
        verify(mockMap).containsKey(null);
    }
}