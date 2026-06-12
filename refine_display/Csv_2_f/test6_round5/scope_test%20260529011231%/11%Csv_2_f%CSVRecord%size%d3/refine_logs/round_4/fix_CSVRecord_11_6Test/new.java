package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_6Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[0]);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        CSVRecord record = createCSVRecord(values);
        Assertions.assertEquals(1000, record.size());
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals("value", record.get(i));
        }
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"first", "second"});
        Assertions.assertEquals(2, record.size());
        Assertions.assertEquals("first", record.get(0));
        Assertions.assertEquals("second", record.get(1));
    }

    @Test
    public void testSize_nullValues() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{null, "value"});
        Assertions.assertEquals(2, record.size());
        Assertions.assertNull(record.get(0));
        Assertions.assertEquals("value", record.get(1));
    }

    @Test
    public void testSize_emptyString() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"", "value"});
        Assertions.assertEquals(2, record.size());
        Assertions.assertEquals("", record.get(0));
        Assertions.assertEquals("value", record.get(1));
    }

    @Test
    public void testSize_specialCharacters() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "@#$%^&*()", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("@#$%^&*()", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_specialCharacterBoundary() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"", null, " "});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("", record.get(0));
        Assertions.assertNull(record.get(1));
        Assertions.assertEquals(" ", record.get(2));
    }

    private CSVRecord createCSVRecord(String[] values) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, 1L);
    }
}