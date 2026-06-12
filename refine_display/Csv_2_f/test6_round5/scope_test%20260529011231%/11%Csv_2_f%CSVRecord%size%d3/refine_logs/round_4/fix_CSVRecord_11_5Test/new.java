package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_5Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        String[] values = {"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 1);
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 2);
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        String[] values = {null, "", " "};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 3);
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals(null, record.get(0));
        Assertions.assertEquals("", record.get(1));
        Assertions.assertEquals(" ", record.get(2));
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 4);
        Assertions.assertEquals(1000, record.size());
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals("value", record.get(i));
        }
    }

    @Test
    public void testSize_nullElements() throws Exception {
        String[] values = {null, null, null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 5);
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals(null, record.get(0));
        Assertions.assertEquals(null, record.get(1));
        Assertions.assertEquals(null, record.get(2));
    }

    @Test
    public void testSize_withMixedValues() throws Exception {
        String[] values = {"value1", null, "value3", "", " "};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 6);
        Assertions.assertEquals(5, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals(null, record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals("", record.get(3));
        Assertions.assertEquals(" ", record.get(4));
    }

    @Test
    public void testSize_withEmptyAndNullValues() throws Exception {
        String[] values = {"", null, "", null, "value"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = createCSVRecord(values, mapping, null, 7);
        Assertions.assertEquals(5, record.size());
        Assertions.assertEquals("", record.get(0));
        Assertions.assertEquals(null, record.get(1));
        Assertions.assertEquals("", record.get(2));
        Assertions.assertEquals(null, record.get(3));
        Assertions.assertEquals("value", record.get(4));
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}