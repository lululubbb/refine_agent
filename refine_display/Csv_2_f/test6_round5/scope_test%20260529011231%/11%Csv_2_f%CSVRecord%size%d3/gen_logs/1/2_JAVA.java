package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_11_1Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[0], new HashMap<>(), null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        Assertions.assertEquals(1, record.size());
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, new HashMap<>(), null, 2);
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Collections.fill(Arrays.asList(values), "value");
        CSVRecord record = new CSVRecord(values, new HashMap<>(), null, 3);
        Assertions.assertEquals(1000, record.size());
    }

    @Test
    public void testSize_withNullValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{null, null}, new HashMap<>(), null, 4);
        Assertions.assertEquals(2, record.size());
    }

    private void setPrivateField(CSVRecord record, String fieldName, Object value) throws Exception {
        Field field = CSVRecord.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(record, value);
    }
}