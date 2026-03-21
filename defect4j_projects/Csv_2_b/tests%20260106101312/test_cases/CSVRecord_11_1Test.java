package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_11_1Test {

    private Constructor<CSVRecord> constructor;

    @BeforeEach
    void setUp() throws Exception {
        constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
    }

    @Test
    @Timeout(8000)
    void testSize_withNonEmptyValuesArray() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        int size = record.size();

        assertEquals(3, size);
    }

    @Test
    @Timeout(8000)
    void testSize_withEmptyValuesArray() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        int size = record.size();

        assertEquals(0, size);
    }

    @Test
    @Timeout(8000)
    void testSize_withNullValuesArray() throws Exception {
        String[] values = new String[] {"x"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        valuesField.set(record, null);

        try {
            record.size();
        } catch (NullPointerException e) {
            // expected
            return;
        }
        throw new AssertionError("Expected NullPointerException when values is null");
    }
}