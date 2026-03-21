package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.fail;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_12_2Test {

    private Constructor<CSVRecord> constructor;

    @BeforeEach
    void setUp() throws Exception {
        constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
    }

    @Test
    @Timeout(8000)
    void testToStringWithValues() throws Exception {
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = constructor.newInstance((Object) values, mapping, "comment", 1L);

        String expected = "[a, b, c]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToStringWithEmptyValues() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 0L);

        String expected = "[]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToStringWithNullValuesField() throws Exception {
        // Create instance with valid values
        String[] values = new String[] { "x" };
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 0L);

        // Use reflection to set private final values field to null
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);

        // Remove final modifier from the field (works in Java 8-11)
        try {
            Field modifiersField = Field.class.getDeclaredField("modifiers");
            modifiersField.setAccessible(true);
            modifiersField.setInt(valuesField, valuesField.getModifiers() & ~Modifier.FINAL);
        } catch (NoSuchFieldException ignored) {
            // In Java 12+, 'modifiers' field is removed, so skip removing final modifier
        }

        valuesField.set(record, null);

        // toString should now throw NullPointerException, but let's verify behavior
        try {
            record.toString();
            fail("Expected NullPointerException when values field is null");
        } catch (NullPointerException e) {
            // Expected, so test passes
        }
    }
}