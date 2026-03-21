package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_12_1Test {

    @Test
    @Timeout(8000)
    void testToString_withValues() {
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);
        String expected = "[a, b, c]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToString_withEmptyValues() {
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 2L);
        String expected = "[]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToString_withNullValuesArray() throws Exception {
        String[] values = new String[] { "x", "y" };
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 3L);

        // Use reflection to set private final field 'values' to null
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);

        // Remove final modifier from the field (works in Java 8-16)
        Field modifiersField = Field.class.getDeclaredField("modifiers");
        modifiersField.setAccessible(true);
        modifiersField.setInt(valuesField, valuesField.getModifiers() & ~Modifier.FINAL);

        valuesField.set(record, null);

        // toString should handle null values gracefully, Arrays.toString(null) returns "null"
        assertEquals("null", record.toString());
    }
}